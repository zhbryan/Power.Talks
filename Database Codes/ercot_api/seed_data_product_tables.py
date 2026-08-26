#!/usr/bin/env python3
"""seed_data_product_tables.py — create + seed one stats_illustrator table per
ERCOT DATA product, loading a single content-date's rows.

Modeled on the existing example table `np3_560_cd_7d_load_fcast_by_fzn`
(posted_datetime injected from the archive posting + the report's own data
columns + loaded_at). Because each report's natural key differs (some keyed by
settlement point, bus, resource, etc.), this generic loader uses a surrogate
`id` primary key plus an index on the detected content-date column, rather than
the example's report-specific composite PK. Column types are inferred from the
CSV (numeric -> double, DST flag -> tinyint, date -> date, timestamp -> datetime,
else varchar/text).

For each emilId it:
  1. lists archive postings in a window around the target date (newest-first),
  2. downloads newest-first until a posting contains rows whose content-date ==
     the target date (the latest available view of that day),
  3. creates `<emil_stem>_<slug>` and inserts those rows.

Usage:
  py -3 seed_data_product_tables.py --date 2026-08-01 NP6-345-CD NP4-190-CD
  py -3 seed_data_product_tables.py --date 2026-08-01 --pilot
  py -3 seed_data_product_tables.py --date 2026-08-01 --all   # every DATA product
"""

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta

import requests

import list_emil_products as L  # reuse auth + credential loading

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(L.PROJECT_ROOT, "Documents Database", "ERCOT.PUBAPI")
LATEST_JSON = os.path.join(OUT_DIR, "emil_products_latest.json")

MAX_DOWNLOADS = 60        # safety cap on postings pulled per report
LIST_PAGE = 1000
WINDOW_BEFORE = 8         # days before target to search (covers 7-day forecasts / DAM)
WINDOW_AFTER = 1          # days after target (covers next-morning actuals postings)

# Sub-hourly products post far too often to seed one-posting-at-a-time; a
# newest-first scan would exhaust MAX_DOWNLOADS before reaching the target day.
# They need a dedicated bulk loader — skip them in --all unless overridden.
HIGHFREQ_MARKERS = ("5 minute", "15 minute", "per sced run", "per rtd run")

# A hand-picked pilot: once-daily / day-ahead posted reports (cheap to seed).
PILOT = ["NP6-345-CD", "NP6-346-CD", "NP4-190-CD",
         "NP4-523-CD", "NP4-33-CD", "NP4-188-CD"]

DATE_HEADER_HINTS = ("deliverydate", "operday", "operatingday", "operatingdate",
                     "operatingdatetime", "businessdate", "tradedate", "date")
HOUR_HEADER_HINTS = ("hourending", "hourbeginning", "deliveryhour", "hour",
                     "intervalending", "interval")


# --- Auth (auto-refreshing, same pattern as backfill_report_archive) ---------

class Auth:
    def __init__(self, user, pwd, key, ttl=2900):
        self.user, self.pwd, self.key, self.ttl = user, pwd, key, ttl
        self._token, self._acquired = None, 0.0

    def refresh(self):
        self._token = L.get_id_token(self.user, self.pwd)
        self._acquired = time.time()

    @property
    def headers(self):
        if self._token is None or (time.time() - self._acquired) > self.ttl:
            self.refresh()
        return {"Authorization": f"Bearer {self._token}",
                "Ocp-Apim-Subscription-Key": self.key}


# --- HTTP with retry / rate-limit handling -----------------------------------

def _retry_wait(resp, attempt):
    ra = resp.headers.get("Retry-After")
    if ra and ra.isdigit():
        return int(ra) + 1
    m = re.search(r"try again in (\d+)\s*second", resp.text, re.IGNORECASE)
    if m:
        return int(m.group(1)) + 1
    return min(60, 2 ** attempt)


def _get(url, auth, params, retries=8):
    for attempt in range(1, retries + 1):
        r = requests.get(url, headers=auth.headers, params=params, timeout=90)
        if r.status_code == 200:
            return r
        if r.status_code == 401 and attempt < retries:
            auth.refresh()
            continue
        if r.status_code in (429, 500, 502, 503) and attempt < retries:
            time.sleep(_retry_wait(r, attempt))
            continue
        raise RuntimeError(f"{url} -> {r.status_code}: {r.text[:200]}")
    return r


def list_archives(auth, emil, dfrom, dto):
    """Return [(docId, postDatetime)] newest-first in [dfrom, dto]."""
    url = f"{L.REPORTS_URL}/archive/{emil.lower()}"
    out = []
    r = _get(url, auth, {"postDatetimeFrom": dfrom + "T00:00:00",
                         "postDatetimeTo": dto + "T23:59:59", "size": LIST_PAGE})
    for a in r.json().get("archives", []):
        out.append((a["docId"], a["postDatetime"].replace("T", " ").split(".")[0]))
    return out


def download_csv(auth, emil, doc_id):
    url = f"{L.REPORTS_URL}/archive/{emil.lower()}"
    r = _get(url, auth, {"download": doc_id})
    if r.content[:2] != b"PK":
        return None
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = next((n for n in z.namelist() if n.lower().endswith(".csv")),
                z.namelist()[0])
    return z.read(name).decode("utf-8", "replace")


# --- CSV typing / content-date detection -------------------------------------

def _parse_date(v):
    v = (v or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(v.split("T")[0] if "T" in v and fmt == "%Y-%m-%d"
                                     else v, fmt).date()
        except ValueError:
            continue
    return None


def _is_float(v):
    v = (v or "").strip()
    if v == "":
        return True  # empty is null, doesn't disqualify a numeric column
    try:
        float(v)
        return True
    except ValueError:
        return False


def _snake(name):
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return re.sub(r"_+", "_", s) or "col"


def detect_date_column(header, rows, target):
    """Return the header name whose values include `target` (a date), preferring
    hinted date headers. Returns None if no column matches the target date."""
    def matches(col_idx):
        return any(_parse_date(r[col_idx]) == target for r in rows if col_idx < len(r))
    hinted = [i for i, h in enumerate(header) if _snake(h).replace("_", "") in
              [x.replace("_", "") for x in DATE_HEADER_HINTS]]
    for i in hinted:
        if matches(i):
            return i
    for i, h in enumerate(header):  # fallback: any header containing date/day
        if ("date" in h.lower() or "day" in h.lower()) and matches(i):
            return i
    return None


def infer_types(header, rows):
    """Return list of ('col_snake', sql_type, kind) for each CSV column."""
    types = []
    for i, h in enumerate(header):
        col = _snake(h)
        vals = [r[i] for r in rows if i < len(r) and (r[i] or "").strip() != ""]
        low = h.lower()
        if "dst" in low:
            types.append((col, "tinyint(1) NOT NULL DEFAULT '0'", "dst"))
        elif any(hint in low.replace(" ", "") for hint in HOUR_HEADER_HINTS):
            types.append((col, "varchar(16)", "str"))
        elif vals and all(_is_float(v) for v in vals):
            types.append((col, "double DEFAULT NULL", "num"))
        else:
            width = max((len(v) for v in vals), default=16)
            sql = "text" if width > 255 else f"varchar({max(16, min(255, width + 16))})"
            types.append((col, sql + " DEFAULT NULL", "str"))
    return types


def coerce(kind, v):
    v = (v or "").strip()
    if kind == "dst":
        return 1 if v.upper() in ("Y", "1", "TRUE") else 0
    if v == "":
        return None
    if kind == "num":
        try:
            return float(v)
        except ValueError:
            return None
    return v


# --- DB ----------------------------------------------------------------------

def db_config():
    return {
        "host": os.environ.get("STATS_DB_HOST", "127.0.0.1"),
        "user": os.environ.get("STATS_DB_USER", "root"),
        "password": os.environ.get("STATS_DB_PASSWORD", ""),
        "database": os.environ.get("STATS_DB_NAME", "stats_illustrator"),
        "port": int(os.environ.get("STATS_DB_PORT", "3306")),
    }


def table_name(emil, name):
    stem = emil.lower().replace("-", "_")
    slug = _snake(name)[:40].rstrip("_")
    return f"{stem}_{slug}" if slug else stem


# --- Per-report seed ---------------------------------------------------------

def seed_one(auth, conn, emil, name, target):
    import csv as _csv
    tgt_date = datetime.strptime(target, "%Y-%m-%d").date()
    dfrom = (tgt_date - timedelta(days=WINDOW_BEFORE)).strftime("%Y-%m-%d")
    dto = (tgt_date + timedelta(days=WINDOW_AFTER)).strftime("%Y-%m-%d")

    archives = list_archives(auth, emil, dfrom, dto)
    if not archives:
        return {"emil": emil, "status": "no-archives", "rows": 0, "table": None}

    header = date_rows = date_col = posted = None
    for n, (doc_id, post_dt) in enumerate(archives, 1):
        if n > MAX_DOWNLOADS:
            return {"emil": emil, "status": f"cap-{MAX_DOWNLOADS}-no-match",
                    "rows": 0, "table": None}
        text = download_csv(auth, emil, doc_id)
        if not text:
            continue
        allrows = list(_csv.reader(io.StringIO(text)))
        if len(allrows) < 2:
            continue
        hdr, body = allrows[0], allrows[1:]
        dci = detect_date_column(hdr, body, tgt_date)
        if dci is None:
            continue
        matched = [r for r in body if dci < len(r) and _parse_date(r[dci]) == tgt_date]
        if matched:
            header, date_rows, date_col, posted = hdr, matched, dci, post_dt
            break

    if not date_rows:
        return {"emil": emil, "status": "date-not-found", "rows": 0, "table": None}

    types = infer_types(header, date_rows)
    tbl = table_name(emil, name)
    cols_sql = ",\n  ".join(f"`{c}` {t}" for c, t, _ in types)
    date_col_snake = types[date_col][0]
    # Force the content-date column to DATE regardless of inference.
    types[date_col] = (date_col_snake, "date NOT NULL", "date")
    cols_sql = ",\n  ".join(
        f"`{c}` {'date NOT NULL' if idx == date_col else t}"
        for idx, (c, t, _) in enumerate(types))

    ddl = (
        f"CREATE TABLE IF NOT EXISTS `{tbl}` (\n"
        f"  `id` bigint NOT NULL AUTO_INCREMENT,\n"
        f"  `posted_datetime` datetime NOT NULL,\n"
        f"  {cols_sql},\n"
        f"  `loaded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
        f"  PRIMARY KEY (`id`),\n"
        f"  KEY `idx_content_date` (`{date_col_snake}`),\n"
        f"  KEY `idx_posted` (`posted_datetime`)\n"
        f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")

    col_names = ["posted_datetime"] + [c for c, _, _ in types]
    placeholders = ",".join(["%s"] * len(col_names))
    insert = (f"INSERT INTO `{tbl}` (" + ",".join(f"`{c}`" for c in col_names) +
              f") VALUES ({placeholders})")

    def build(r):
        vals = [posted]
        for idx, (c, _t, kind) in enumerate(types):
            raw = r[idx] if idx < len(r) else ""
            if idx == date_col:
                d = _parse_date(raw)
                vals.append(d.strftime("%Y-%m-%d") if d else target)
            else:
                vals.append(coerce(kind, raw))
        return vals

    with conn.cursor() as cur:
        cur.execute(ddl)
        # Idempotent reseed: clear this content-date before loading.
        cur.execute(f"DELETE FROM `{tbl}` WHERE `{date_col_snake}`=%s", (target,))
        cur.executemany(insert, [build(r) for r in date_rows])
    conn.commit()
    return {"emil": emil, "status": "ok", "rows": len(date_rows),
            "table": tbl, "posted": posted}


# --- Main --------------------------------------------------------------------

def load_catalog():
    with open(LATEST_JSON, encoding="utf-8") as f:
        doc = json.load(f)
    return {p["emilId"]: p for p in doc["products"] if p.get("contentType") == "DATA"}


def existing_stems(conn):
    """Table-name stems already present, so --all won't duplicate a built table
    (e.g. the curated np3_560_cd_7d_load_fcast_by_fzn)."""
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema=%s", (db_config()["database"],))
        return {r[0] for r in cur.fetchall()}


def _has_table(stems, emil):
    stem = emil.lower().replace("-", "_")
    return any(t == stem or t.startswith(stem + "_") for t in stems)


def _is_highfreq(product):
    freq = (product.get("generationFrequency") or "").lower()
    return any(m in freq for m in HIGHFREQ_MARKERS)


def main():
    ap = argparse.ArgumentParser(description="Seed stats_illustrator DATA-product tables.")
    ap.add_argument("emils", nargs="*", help="EMIL ids to seed (e.g. NP6-345-CD)")
    ap.add_argument("--date", required=True, help="content date to load (YYYY-MM-DD)")
    ap.add_argument("--pilot", action="store_true", help="seed the built-in pilot set")
    ap.add_argument("--all", action="store_true", help="seed every DATA product")
    ap.add_argument("--include-highfreq", action="store_true",
                    help="also attempt sub-hourly (5/15-min, SCED, RTD) products")
    ap.add_argument("--reseed-existing", action="store_true",
                    help="don't skip products that already have a table")
    args = ap.parse_args()

    catalog = load_catalog()
    if args.all:
        emils = list(catalog.keys())
    elif args.pilot:
        emils = PILOT
    else:
        emils = args.emils
    if not emils:
        sys.exit("Nothing to do: pass EMIL ids, --pilot, or --all.")

    import pymysql
    cfg = db_config()
    conn = pymysql.connect(host=cfg["host"], user=cfg["user"], password=cfg["password"],
                           database=cfg["database"], port=cfg["port"], autocommit=False)
    stems = existing_stems(conn)

    user, pwd, key = L.load_credentials()
    auth = Auth(user, pwd, key)

    results = []
    for emil in emils:
        p = catalog.get(emil)
        if not p:
            print(f"{emil:<12} {'not-data':<20} (skipped)")
            results.append({"emil": emil, "status": "not-data", "rows": 0})
            continue
        if not args.reseed_existing and _has_table(stems, emil):
            print(f"{emil:<12} {'exists-skip':<20} (table already present)")
            results.append({"emil": emil, "status": "exists-skip", "rows": 0})
            continue
        if not args.include_highfreq and _is_highfreq(p):
            print(f"{emil:<12} {'highfreq-skip':<20} "
                  f"({p.get('generationFrequency')})")
            results.append({"emil": emil, "status": "highfreq-skip", "rows": 0})
            continue
        try:
            res = seed_one(auth, conn, emil, p["name"], args.date)
        except Exception as e:  # noqa: BLE001 — keep going through the batch
            res = {"emil": emil, "status": f"error: {e}", "rows": 0, "table": None}
        tag = res["status"]
        print(f"{emil:<12} {tag:<20} rows={res['rows']:<7} "
              f"{res.get('table') or ''}")
        results.append(res)

    conn.close()
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nSeeded {ok}/{len(results)} tables for {args.date}.")


if __name__ == "__main__":
    main()
