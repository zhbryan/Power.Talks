#!/usr/bin/env python3
"""
Backfill the FULL historical archive of one ERCOT EMIL report into the
stats_illustrator DB table (or, with --sql-out, into a loadable .sql file).

The live query endpoint only keeps a ~5-month rolling window; the deep history
lives in the archive endpoint as one posted file per hour. For NP3-560-CD that
is ~66,900 files back to 2019-01-01 (~12.8M rows). This walks the archive
listing, downloads each posting's zipped CSV, parses it, injects the posting's
postedDatetime (which is archive metadata, not a CSV column), and upserts.

Design for scale:
  * Resumable  — processed docIds are recorded in a state file; re-runs skip them.
  * Bounded    — --since / --until / --limit let you backfill in slices.
  * Polite     — --sleep throttles downloads; transient errors retry.
  * DB-optional— loads via pymysql when available; --sql-out writes SQL instead
                 (works with no DB running, load later with the mysql client).

This script is specific to NP3-560-CD's schema (see REPORT config). To backfill
another "Current Day Report" with the same posted/delivery/hour/DST shape, copy
REPORT and adjust columns + table.

Usage:
  # Try a small slice as SQL (no DB needed) to eyeball the output:
  py -3 backfill_report_archive.py --since 2019-01-01 --limit 3 --sql-out sample.sql
  # Backfill a year straight into MySQL (pymysql + running DB required):
  py -3 backfill_report_archive.py --since 2019-01-01 --until 2019-12-31
  # Resume / continue everything (skips already-loaded postings):
  py -3 backfill_report_archive.py
"""

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime

import requests

import list_emil_products as L   # reuse auth + credential loading

# --- Report-specific config (NP3-560-CD) ------------------------------------
REPORT = {
    "emilId": "NP3-560-CD",
    "table": "np3_560_cd_7d_load_fcast_by_fzn",
    # CSV header -> table column. postedDatetime is injected from archive meta.
    "csv_map": {
        "DeliveryDate": "delivery_date",
        "HourEnding": "hour_ending",
        "North": "north",
        "South": "south",
        "West": "west",
        "Houston": "houston",
        "SystemTotal": "system_total",
        "DSTFlag": "dst_flag",
    },
    # Column order written to the DB / SQL (posted_datetime first, injected).
    "columns": ["posted_datetime", "delivery_date", "hour_ending", "dst_flag",
                "north", "south", "west", "houston", "system_total"],
    "key_columns": ["posted_datetime", "delivery_date", "hour_ending", "dst_flag"],
}

ARCHIVE_URL = f"{L.REPORTS_URL}/archive/{REPORT['emilId'].lower()}"
STATE_DIR = os.path.join(L.PROJECT_ROOT, "Documents Database", "STATS.ILLUSTRATOR",
                         REPORT["emilId"])
STATE_FILE = os.path.join(STATE_DIR, "_backfill_state.json")
LIST_PAGE = 1000


# --- Auth (auto-refreshing) --------------------------------------------------

class Auth:
    """The ERCOT ID token is valid ~1h with no refresh grant, so a multi-hour
    backfill must re-fetch it. This hands out fresh headers, re-authenticating
    proactively before the TTL and reactively when the server says 401."""

    def __init__(self, user, pwd, key, ttl=2900):   # ~48 min < 60 min token life
        self.user, self.pwd, self.key, self.ttl = user, pwd, key, ttl
        self._token = None
        self._acquired = 0.0

    def refresh(self):
        self._token = L.get_id_token(self.user, self.pwd)
        self._acquired = time.time()

    @property
    def headers(self):
        if self._token is None or (time.time() - self._acquired) > self.ttl:
            self.refresh()
        return {"Authorization": f"Bearer {self._token}",
                "Ocp-Apim-Subscription-Key": self.key}


# --- Value coercion ----------------------------------------------------------

def _iso_date(mmddyyyy):
    """'08/20/2026' -> '2026-08-20'."""
    return datetime.strptime(mmddyyyy, "%m/%d/%Y").strftime("%Y-%m-%d")


def _posted(dt):
    """'2026-08-20T00:30:00.000' -> '2026-08-20 00:30:00'."""
    return dt.replace("T", " ").split(".")[0]


def _num(v):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_csv(text, posted_dt):
    """Yield dict rows keyed by table column, injecting posted_datetime."""
    import csv
    reader = csv.DictReader(io.StringIO(text))
    for r in reader:
        row = {"posted_datetime": posted_dt}
        for csv_col, tbl_col in REPORT["csv_map"].items():
            raw = r.get(csv_col)
            if tbl_col == "delivery_date":
                row[tbl_col] = _iso_date(raw) if raw else None
            elif tbl_col == "hour_ending":
                row[tbl_col] = (raw or "").strip()
            elif tbl_col == "dst_flag":
                row[tbl_col] = 1 if (raw or "").strip().upper() in ("Y", "1", "TRUE") else 0
            else:
                row[tbl_col] = _num(raw)
        yield row


# --- Rate-limit aware HTTP ---------------------------------------------------

def _retry_wait(resp, attempt):
    """Seconds to wait before retrying. ERCOT 429s advise a cooldown via the
    Retry-After header or a 'Try again in N seconds' message — honor it."""
    ra = resp.headers.get("Retry-After")
    if ra and ra.isdigit():
        return int(ra) + 1
    m = re.search(r"try again in (\d+)\s*second", resp.text, re.IGNORECASE)
    if m:
        return int(m.group(1)) + 1
    return min(60, 2 ** attempt)   # exponential backoff fallback


# --- Archive listing + download ---------------------------------------------

def iter_archives(auth, since=None, until=None):
    """Yield (docId, postedDatetime) newest-first, filtered to [since, until]."""
    page, total_pages = 1, None
    while True:
        r = _get(ARCHIVE_URL, auth, params={"page": page, "size": LIST_PAGE})
        j = r.json()
        meta = j.get("_meta") or {}
        total_pages = total_pages or meta.get("totalPages")
        for a in j.get("archives", []):
            posted = _posted(a["postDatetime"])
            day = posted[:10]
            if since and day < since:
                continue
            if until and day > until:
                continue
            yield a["docId"], posted
        if total_pages and page >= total_pages:
            break
        if not j.get("archives"):
            break
        page += 1


def download_posting(doc_id, auth, retries=8):
    """Download + unzip a posting, return the inner CSV text."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(ARCHIVE_URL, headers=auth.headers,
                             params={"download": doc_id}, timeout=120)
            if r.status_code == 200 and r.content[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(r.content))
                name = next((n for n in z.namelist() if n.lower().endswith(".csv")),
                            z.namelist()[0])
                return z.read(name).decode("utf-8", "replace")
            if r.status_code == 401:          # token expired mid-run -> re-auth
                auth.refresh()
                continue
            if r.status_code in (429, 500, 502, 503):
                time.sleep(_retry_wait(r, attempt))
                continue
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except (requests.RequestException, zipfile.BadZipFile):
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return None


def _get(url, auth, params, retries=8):
    for attempt in range(1, retries + 1):
        r = requests.get(url, headers=auth.headers, params=params, timeout=60)
        if r.status_code == 200:
            return r
        if r.status_code == 401 and attempt < retries:
            print("  … 401 on listing; re-authenticating")
            auth.refresh()
            continue
        if r.status_code in (429, 500, 502, 503) and attempt < retries:
            wait = _retry_wait(r, attempt)
            print(f"  … {r.status_code} on listing; waiting {wait}s")
            time.sleep(wait)
            continue
        sys.exit(f"ERROR: {url} -> {r.status_code}: {r.text[:200]}")
    return r


# --- Sinks: MySQL or SQL file -----------------------------------------------

class SqlFileSink:
    """Writes INSERT ... ON DUPLICATE KEY UPDATE statements to a .sql file."""

    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")
        self.f.write(f"-- Backfill {REPORT['emilId']} -> {REPORT['table']}\n"
                     f"USE stats_illustrator;\n")
        cols = REPORT["columns"]
        upd = ", ".join(f"{c}=VALUES({c})" for c in cols if c not in REPORT["key_columns"])
        self._prefix = f"INSERT INTO {REPORT['table']} (" + ", ".join(cols) + ") VALUES\n"
        self._suffix = f"\nON DUPLICATE KEY UPDATE {upd};\n"

    @staticmethod
    def _lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, (int, float)):
            return repr(v)
        return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"

    def write_rows(self, rows):
        if not rows:
            return
        vals = [",\n".join("(" + ", ".join(self._lit(r[c]) for c in REPORT["columns"]) + ")"
                           for r in rows)]
        self.f.write(self._prefix + vals[0] + self._suffix)

    def close(self):
        self.f.close()


class MySqlSink:
    """Batched upsert into MySQL via pymysql."""

    def __init__(self):
        try:
            import pymysql
        except ImportError:
            sys.exit("ERROR: pymysql not installed (`pip install pymysql`). "
                     "Or run with --sql-out to produce a loadable .sql file instead.")
        cfg = self._config()
        self.conn = pymysql.connect(
            host=cfg["host"], user=cfg["user"], password=cfg["password"],
            database=cfg["database"], port=cfg.get("port", 3306), autocommit=False)
        cols = REPORT["columns"]
        ph = ", ".join(["%s"] * len(cols))
        upd = ", ".join(f"{c}=VALUES({c})" for c in cols if c not in REPORT["key_columns"])
        self.sql = (f"INSERT INTO {REPORT['table']} (" + ", ".join(cols) +
                    f") VALUES ({ph}) ON DUPLICATE KEY UPDATE {upd}")

    @staticmethod
    def _config():
        f = os.path.join(L.HERE, "db_config.json")
        if os.path.exists(f):
            return json.load(open(f, encoding="utf-8"))
        return {
            "host": os.environ.get("STATS_DB_HOST", "127.0.0.1"),
            "user": os.environ.get("STATS_DB_USER", "root"),
            "password": os.environ.get("STATS_DB_PASSWORD", ""),
            "database": os.environ.get("STATS_DB_NAME", "stats_illustrator"),
            "port": int(os.environ.get("STATS_DB_PORT", "3306")),
        }

    def write_rows(self, rows):
        if not rows:
            return
        data = [tuple(r[c] for c in REPORT["columns"]) for r in rows]
        with self.conn.cursor() as cur:
            cur.executemany(self.sql, data)
        self.conn.commit()

    def close(self):
        self.conn.close()


# --- State (resume) ----------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        s = json.load(open(STATE_FILE, encoding="utf-8"))
        s["done"] = set(s.get("done", []))
        return s
    return {"done": set(), "rows_loaded": 0}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    out = dict(state)
    out["done"] = sorted(state["done"])
    out["updated"] = datetime.now().isoformat(timespec="seconds")
    json.dump(out, open(STATE_FILE, "w", encoding="utf-8"), indent=2)


# --- Main --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Backfill an ERCOT report archive.")
    ap.add_argument("--since", help="earliest delivery/posting day YYYY-MM-DD")
    ap.add_argument("--until", help="latest day YYYY-MM-DD")
    ap.add_argument("--limit", type=int, help="max postings to process this run")
    ap.add_argument("--sleep", type=float, default=0.25, help="seconds between downloads")
    ap.add_argument("--sql-out", help="write SQL to this file instead of loading a DB")
    ap.add_argument("--reload", action="store_true", help="ignore state; re-process")
    args = ap.parse_args()

    user, pwd, key = L.load_credentials()
    print("Authenticating…")
    auth = Auth(user, pwd, key)
    auth.refresh()   # log in now so any credential error surfaces immediately

    state = {"done": set(), "rows_loaded": 0} if args.reload else load_state()
    sink = SqlFileSink(args.sql_out) if args.sql_out else MySqlSink()
    where = f" since={args.since or '-'} until={args.until or '-'} limit={args.limit or 'all'}"
    print(f"Backfilling {REPORT['emilId']} ->"
          f" {'SQL file ' + args.sql_out if args.sql_out else 'MySQL ' + REPORT['table']}{where}")

    processed = rows_total = 0
    try:
        for doc_id, posted in iter_archives(auth, args.since, args.until):
            if not args.reload and doc_id in state["done"]:
                continue
            if args.limit and processed >= args.limit:
                break
            try:
                csv_text = download_posting(doc_id, auth)
                rows = list(parse_csv(csv_text, posted))
                sink.write_rows(rows)
            except Exception as e:                      # skip a bad posting, keep going
                print(f"  ! {posted} doc {doc_id}: {e}")
                continue
            state["done"].add(doc_id)
            state["rows_loaded"] = state.get("rows_loaded", 0) + len(rows)
            processed += 1
            rows_total += len(rows)
            if processed % 25 == 0:
                save_state(state)
                print(f"  {processed} postings, {rows_total} rows this run "
                      f"(latest {posted})")
            time.sleep(args.sleep)
    finally:
        sink.close()
        save_state(state)

    print(f"\nDone this run: {processed} postings, {rows_total} rows.")
    print(f"Cumulative postings loaded: {len(state['done'])}. State: {STATE_FILE}")
    if args.sql_out:
        print(f"Load it with:  mysql -u root stats_illustrator < \"{args.sql_out}\"")


if __name__ == "__main__":
    main()
