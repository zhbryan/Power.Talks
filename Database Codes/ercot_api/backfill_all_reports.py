#!/usr/bin/env python3
"""backfill_all_reports.py — generic, resumable historical backfill of the
stats_illustrator DATA-product tables.

Unlike backfill_report_archive.py (hardcoded to NP3-560-CD), this works for ANY
already-created table: it finds each report's table, introspects its columns,
and loads every archive posting in [--since, --until] into it — reusing the same
column names (_snake) and value coercion the seeder used to build the table, so
it transparently handles both table shapes (daily: report date column typed
DATE; rolling/latest: columns verbatim + derived `content_date`).

Default scope is "Tier B": every DATA product EXCEPT sub-hourly (5/15-min,
per-SCED — too many postings / rows), RTD (excluded everywhere), and the
hand-curated NP3-560-CD (owned by backfill_report_archive.py). Override with
--tier {b,all} or explicit EMIL ids.

Resumable + idempotent: per report, a state file records a one-time window
pre-clear (DELETE WHERE posted_datetime >= since) plus the docIds already loaded,
so re-runs continue without duplicating. Polite: --sleep throttles; 401/429 are
retried with backoff (via the shared HTTP helpers).

Usage:
  py -3 backfill_all_reports.py                       # Tier B, since 2026-07-01
  py -3 backfill_all_reports.py --since 2026-07-01 --until 2026-08-29
  py -3 backfill_all_reports.py --tier all            # every non-RTD/curated table
  py -3 backfill_all_reports.py NP4-190-CD NP6-345-CD # explicit reports
  py -3 backfill_all_reports.py --reload NP4-190-CD   # rebuild from scratch
"""

import argparse
import csv as _csv
import io
import json
import os
import sys
import time
from datetime import datetime

import list_emil_products as L
import seed_data_product_tables as S   # reuse auth, HTTP, typing, helpers

STATE_ROOT = os.path.join(L.PROJECT_ROOT, "Documents Database", "STATS.ILLUSTRATOR")
LIST_PAGE = 1000
META_COLS = {"id", "posted_datetime", "loaded_at", "content_date"}


# --- Lock: signal the nightly seed to yield while we run --------------------

def write_lock(scope):
    os.makedirs(os.path.dirname(S.LOCK_PATH), exist_ok=True)
    json.dump({"pid": os.getpid(), "scope": scope,
               "started": datetime.now().isoformat(timespec="seconds")},
              open(S.LOCK_PATH, "w", encoding="utf-8"))


def touch_lock():
    """Refresh the lock mtime so the seed sees it as fresh (see LOCK_STALE_SECONDS)."""
    try:
        os.utime(S.LOCK_PATH, None)
    except OSError:
        pass


def remove_lock():
    try:
        os.remove(S.LOCK_PATH)
    except OSError:
        pass


# --- Archive listing (paged, server-side date filter) ------------------------

def list_all_archives(auth, emil, since, until):
    """All (docId, postedDatetime) in [since, until], returned oldest-first."""
    url = f"{L.REPORTS_URL}/archive/{emil.lower()}"
    out, page, total = [], 1, None
    while True:
        r = S._get(url, auth, {"postDatetimeFrom": since + "T00:00:00",
                               "postDatetimeTo": until + "T23:59:59",
                               "page": page, "size": LIST_PAGE})
        j = r.json()
        total = total or (j.get("_meta") or {}).get("totalPages")
        archs = j.get("archives", [])
        for a in archs:
            out.append((a["docId"], a["postDatetime"].replace("T", " ").split(".")[0]))
        if (total and page >= total) or not archs:
            break
        page += 1
    out.sort(key=lambda t: t[1])   # 'YYYY-MM-DD HH:MM:SS' sorts chronologically
    return out


# --- Table introspection -----------------------------------------------------

def find_table(conn, emil):
    stem = emil.lower().replace("-", "_")
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=%s", (S.db_config()["database"],))
        for (t,) in sorted(cur.fetchall()):
            if t == stem or t.startswith(stem + "_"):
                return t
    return None


def _kind(sql_type):
    t = sql_type.lower()
    if t.startswith("date"):
        return "date"
    if t.startswith(("double", "float", "decimal")):
        return "num"
    if t.startswith("tinyint"):
        return "dst"
    return "str"


def table_spec(conn, tbl):
    """Return (report_cols=[(name, kind)], has_content_date)."""
    with conn.cursor() as cur:
        cur.execute(f"SHOW COLUMNS FROM `{tbl}`")
        cols = [(r[0], r[1]) for r in cur.fetchall()]
    report = [(c, _kind(t)) for c, t in cols if c not in META_COLS]
    has_cd = any(c == "content_date" for c, _ in cols)
    return report, has_cd


def _coerce(kind, raw):
    raw = (raw or "").strip()
    if kind == "dst":
        return 1 if raw.upper() in ("Y", "1", "TRUE") else 0
    if raw == "":
        return None
    if kind == "num":
        try:
            return float(raw)
        except ValueError:
            return None
    if kind == "date":
        d = S._parse_date(raw)
        return d.strftime("%Y-%m-%d") if d else None
    return raw


# --- State (resume) ----------------------------------------------------------

def _state_path(emil):
    return os.path.join(STATE_ROOT, emil, "_backfill_all_state.json")


def load_state(emil):
    p = _state_path(emil)
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        s["done"] = set(s.get("done", []))
        return s
    return {"precleared": False, "done": set(), "rows": 0}


def save_state(emil, state):
    os.makedirs(os.path.join(STATE_ROOT, emil), exist_ok=True)
    out = dict(state, done=sorted(state["done"]),
               updated=datetime.now().isoformat(timespec="seconds"))
    json.dump(out, open(_state_path(emil), "w", encoding="utf-8"), indent=2)


# --- Per-report backfill -----------------------------------------------------

def backfill_report(auth, conn, emil, name, since, until, sleep, reload_):
    tbl = find_table(conn, emil)
    if not tbl:
        return {"emil": emil, "status": "no-table", "postings": 0, "rows": 0}
    report_cols, has_cd = table_spec(conn, tbl)
    insert_names = ["posted_datetime"] + [c for c, _ in report_cols] \
        + (["content_date"] if has_cd else [])
    placeholders = ",".join(["%s"] * len(insert_names))
    insert_sql = (f"INSERT INTO `{tbl}` (" + ",".join(f"`{c}`" for c in insert_names)
                  + f") VALUES ({placeholders})")

    state = {"precleared": False, "done": set(), "rows": 0} if reload_ else load_state(emil)

    archives = list_all_archives(auth, emil, since, until)
    if not archives:
        return {"emil": emil, "status": "no-archives", "postings": 0, "rows": 0}

    # One-time window pre-clear so the seeder's recent snapshot isn't duplicated.
    if reload_ or not state["precleared"]:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM `{tbl}` WHERE `posted_datetime` >= %s",
                        (since + " 00:00:00",))
        conn.commit()
        state["precleared"] = True
        save_state(emil, state)

    done = state["done"]
    postings = rows_run = 0
    for doc_id, posted in archives:
        if doc_id in done:
            continue
        try:
            text = S.download_csv(auth, emil, doc_id)
            if not text:
                done.add(doc_id)
                continue
            allrows = list(_csv.reader(io.StringIO(text)))
            if len(allrows) < 2:
                done.add(doc_id)
                continue
            header, body = allrows[0], allrows[1:]
            col_idx = {S._snake(h): i for i, h in enumerate(header)}
            cdi = S.detect_any_date_column(header, body) if has_cd else None

            def build(r):
                vals = [posted]
                for c, kind in report_cols:
                    i = col_idx.get(c)
                    vals.append(_coerce(kind, r[i] if i is not None and i < len(r) else ""))
                if has_cd:
                    cd = None
                    if cdi is not None and cdi < len(r):
                        d = S._parse_date(r[cdi])
                        cd = d.strftime("%Y-%m-%d") if d else None
                    vals.append(cd or posted[:10])
                return vals

            with conn.cursor() as cur:
                cur.executemany(insert_sql, [build(r) for r in body])
            conn.commit()
            done.add(doc_id)
            postings += 1
            rows_run += len(body)
        except Exception as e:  # noqa: BLE001 — skip a bad posting, keep going
            print(f"    ! {emil} {posted} doc {doc_id}: {str(e)[:150]}")
            continue
        if postings % 25 == 0:
            state["rows"] = state.get("rows", 0) + rows_run
            save_state(emil, state)
            touch_lock()   # keep the lock fresh through long reports
            print(f"    {emil}: {postings}/{len(archives)} postings, "
                  f"{rows_run} rows this run (latest {posted})")
            rows_run = 0
        time.sleep(sleep)

    state["rows"] = state.get("rows", 0) + rows_run
    save_state(emil, state)
    return {"emil": emil, "status": "ok", "postings": postings,
            "rows": len(done), "table": tbl}


# --- Scope + main ------------------------------------------------------------

def tier_b_emils(catalog):
    """Every non-RTD, non-curated, non-sub-hourly DATA product."""
    out = []
    for emil, p in catalog.items():
        if S._is_excluded(p) or emil in S.CURATED_SKIP or S._is_highfreq(p):
            continue
        out.append(emil)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description="Generic resumable ERCOT table backfill.")
    ap.add_argument("emils", nargs="*", help="explicit EMIL ids (overrides --tier)")
    ap.add_argument("--since", default="2026-07-01", help="earliest posting day (YYYY-MM-DD)")
    ap.add_argument("--until", default=datetime.now().strftime("%Y-%m-%d"),
                    help="latest posting day (YYYY-MM-DD; default today)")
    ap.add_argument("--tier", choices=["b", "all"], default="b",
                    help="b = exclude sub-hourly (default); all = every non-RTD/curated table")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between downloads")
    ap.add_argument("--reload", action="store_true", help="ignore state; rebuild the window")
    args = ap.parse_args()

    catalog = S.load_catalog()
    if args.emils:
        emils = args.emils
    elif args.tier == "all":
        emils = sorted(e for e, p in catalog.items()
                       if not S._is_excluded(p) and e not in S.CURATED_SKIP)
    else:
        emils = tier_b_emils(catalog)

    import pymysql
    cfg = S.db_config()
    conn = pymysql.connect(host=cfg["host"], user=cfg["user"], password=cfg["password"],
                           database=cfg["database"], port=cfg["port"], autocommit=False)
    user, pwd, key = L.load_credentials()
    auth = S.Auth(user, pwd, key)

    print(f"Backfill {len(emils)} reports  [{args.since} .. {args.until}]  "
          f"tier={args.tier if not args.emils else 'explicit'}")
    scope = " ".join(args.emils) if args.emils else f"tier-{args.tier}"
    write_lock(f"{scope} [{args.since}..{args.until}]")
    t0 = time.time()
    results = []
    try:
        for n, emil in enumerate(emils, 1):
            touch_lock()
            p = catalog.get(emil)
            if not p:
                print(f"[{n}/{len(emils)}] {emil:<12} not-data (skip)")
                continue
            print(f"[{n}/{len(emils)}] {emil:<12} {p['name'][:50]}")
            try:
                res = backfill_report(auth, conn, emil, p["name"], args.since, args.until,
                                      args.sleep, args.reload)
            except Exception as e:  # noqa: BLE001
                res = {"emil": emil, "status": f"error: {str(e)[:150]}", "postings": 0, "rows": 0}
            print(f"           -> {res['status']}  postings={res['postings']}  "
                  f"total_docs={res.get('rows', 0)}  {res.get('table', '')}")
            results.append(res)
    finally:
        remove_lock()

    conn.close()
    ok = sum(1 for r in results if r["status"] == "ok")
    tot = sum(r["postings"] for r in results)
    print(f"\nDone: {ok}/{len(results)} reports, {tot} postings loaded this run, "
          f"{(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
