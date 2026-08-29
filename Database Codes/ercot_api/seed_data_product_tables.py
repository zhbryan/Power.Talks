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
  py -3 seed_data_product_tables.py --date 2026-08-01 --all   # every DATA product (RTD excluded)
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
HF_POSTINGS = 24          # high-freq: how many newest postings to ingest per run
LIST_PAGE = 1000
WINDOW_BEFORE = 8         # days before target to search (covers 7-day forecasts / DAM)
WINDOW_AFTER = 1          # days after target (covers next-morning actuals postings)

# RTD products are excluded entirely — never listed, created, or seeded (project
# decision: RTD data is out of scope). Excluded either by posting frequency
# ("Event - Per RTD Run") OR by an "RTD" token in the report name (e.g.
# NP6-970-CD "RTD Indicative LMPs", which posts on a 5-minute chron).
EXCLUDE_MARKERS = ("per rtd run",)
NAME_EXCLUDE_RE = re.compile(r"\brtd\b", re.IGNORECASE)

# Sub-hourly / high-frequency products spread a single operating day across many
# small postings. For these we scan the window and ACCUMULATE the target-date
# rows across every posting (deduping identical rows, newest posting wins),
# rather than trusting one posting to hold the whole day. Normal-cadence reports
# stop at the first posting that already contains the full day.
HIGHFREQ_MARKERS = ("5 minute", "15 minute", "per sced run")

# Hand-curated products the generic seeder must NOT touch — they have a bespoke
# table + a dedicated loader (NP3-560-CD is owned by backfill_report_archive.py,
# table np3_560_cd_7d_load_fcast_by_fzn). Skipped even with --reseed-existing so
# the nightly run never recreates a generically-named duplicate.
CURATED_SKIP = {"NP3-560-CD"}

# A hand-picked pilot: once-daily / day-ahead posted reports (cheap to seed).
PILOT = ["NP6-345-CD", "NP6-346-CD", "NP4-190-CD",
         "NP4-523-CD", "NP4-33-CD", "NP4-188-CD"]

# The "delayed set": reports the --date (yesterday) path can't satisfy — content
# published on a delay (60-day / 2-day / 3-day disclosures, corrections), posted
# as-needed, or whose date column the daily loader can't detect. These are
# skipped by the --date pass (so it doesn't waste downloads failing on them) and
# refreshed instead by a dedicated nightly `--latest --delayed` pass, which loads
# each report's most recent available posting. Keep in sync with the checklist:
# any product that only builds via --latest belongs here.
DELAYED = [
    "NP1-301", "NP1-302", "NP3-257-EX", "NP3-765-CD", "NP3-906-EX", "NP3-907-EX",
    "NP3-908-ER", "NP3-909-ER", "NP3-910-ER", "NP3-911-ER", "NP3-914-EX",
    "NP3-915-EX", "NP3-916-EX", "NP3-965-ER", "NP3-966-ER", "NP3-987-EX",
    "NP3-990-EX", "NP3-991-EX", "NP4-159-CD", "NP4-179-CD", "NP4-196-M",
    "NP4-197-M", "NP4-215-CD", "NP4-231-CD", "NP4-791-CD", "NP5-108-CD",
    "NP5-754-CD", "NP6-625-CD", "NP6-626-CD", "NP6-86-CD",
]

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
    for fmt in ("%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d"):
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


def detect_any_date_column(header, rows):
    """Return the index of the column that carries a date, WITHOUT requiring a
    specific target — used for high-frequency reports whose date lives in an
    interval/timestamp column (e.g. INTERVAL_ENDING = "08/28/2026 16:45").
    Prefers hinted headers, then interval/timestamp/date/day-named columns, then
    any column whose values mostly parse as dates. Returns None if none do."""
    def parses(idx):
        vals = [r[idx] for r in rows if idx < len(r) and (r[idx] or "").strip() != ""]
        return bool(vals) and sum(1 for v in vals if _parse_date(v)) >= max(1, len(vals) // 2)
    hinted = [i for i, h in enumerate(header) if _snake(h).replace("_", "") in
              [x.replace("_", "") for x in DATE_HEADER_HINTS]]
    for i in hinted:
        if parses(i):
            return i
    for i, h in enumerate(header):
        low = h.lower()
        if any(k in low for k in ("interval", "timestamp", "date", "day", "time")) and parses(i):
            return i
    for i in range(len(header)):
        if parses(i):
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

def _create_and_load(conn, tbl, col_defs, content_date_col, insert_names,
                     rows_values, delete_dates):
    """Create `tbl` (if needed) and idempotently load rows_values, first clearing
    the content-dates being loaded. col_defs is [(col, sql_type)] for the report
    columns between posted_datetime and loaded_at; content_date_col is the DATE
    column to index/dedup on; insert_names are the insert column order."""
    cols_sql = ",\n  ".join(f"`{c}` {t}" for c, t in col_defs)
    ddl = (
        f"CREATE TABLE IF NOT EXISTS `{tbl}` (\n"
        f"  `id` bigint NOT NULL AUTO_INCREMENT,\n"
        f"  `posted_datetime` datetime NOT NULL,\n"
        f"  {cols_sql},\n"
        f"  `loaded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
        f"  PRIMARY KEY (`id`),\n"
        f"  KEY `idx_content_date` (`{content_date_col}`),\n"
        f"  KEY `idx_posted` (`posted_datetime`)\n"
        f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")
    placeholders = ",".join(["%s"] * len(insert_names))
    insert = (f"INSERT INTO `{tbl}` (" + ",".join(f"`{c}`" for c in insert_names) +
              f") VALUES ({placeholders})")
    with conn.cursor() as cur:
        cur.execute(ddl)
        if delete_dates:
            ph = ",".join(["%s"] * len(delete_dates))
            cur.execute(f"DELETE FROM `{tbl}` WHERE `{content_date_col}` IN ({ph})",
                        list(delete_dates))
        cur.executemany(insert, rows_values)
    conn.commit()


def _seed_daily(auth, conn, emil, name, target):
    """Once-daily / hourly / event reports: one posting holds the whole content
    day. Pull the newest posting containing `target`, key the table on that DATE
    column, and reload just that content-date (idempotent)."""
    import csv as _csv
    tgt_date = datetime.strptime(target, "%Y-%m-%d").date()
    dfrom = (tgt_date - timedelta(days=WINDOW_BEFORE)).strftime("%Y-%m-%d")
    dto = (tgt_date + timedelta(days=WINDOW_AFTER)).strftime("%Y-%m-%d")

    archives = list_archives(auth, emil, dfrom, dto)
    if not archives:
        return {"emil": emil, "status": "no-archives", "rows": 0, "table": None}

    header = date_col = posted = None
    date_rows = None
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
    date_col_snake = types[date_col][0]
    col_defs = [(c, "date NOT NULL" if idx == date_col else t)
                for idx, (c, t, _) in enumerate(types)]
    insert_names = ["posted_datetime"] + [c for c, _, _ in types]

    def build(r):
        vals = [posted]
        for idx, (_c, _t, kind) in enumerate(types):
            raw = r[idx] if idx < len(r) else ""
            if idx == date_col:
                d = _parse_date(raw)
                vals.append(d.strftime("%Y-%m-%d") if d else target)
            else:
                vals.append(coerce(kind, raw))
        return vals

    tbl = table_name(emil, name)
    _create_and_load(conn, tbl, col_defs, date_col_snake, insert_names,
                     [build(r) for r in date_rows], [target])
    return {"emil": emil, "status": "ok", "rows": len(date_rows),
            "table": tbl, "posted": posted}


def _seed_highfreq(auth, conn, emil, name, target):
    """Sub-hourly reports (5/15-min, per-SCED) post a tiny slice every few
    minutes; assembling a specific past day would blow the download budget. We
    instead ingest the newest HF_POSTINGS postings (the current rolling window),
    keep every column verbatim (the interval timestamp is preserved as text so
    sub-hour resolution survives), and add a derived `content_date` DATE for
    indexing/dedup. Reloads only the content-dates seen (idempotent)."""
    import csv as _csv
    tgt_date = datetime.strptime(target, "%Y-%m-%d").date()
    dfrom = (tgt_date - timedelta(days=1)).strftime("%Y-%m-%d")
    dto = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")

    archives = list_archives(auth, emil, dfrom, dto)
    if not archives:
        return {"emil": emil, "status": "no-archives", "rows": 0, "table": None}

    header = date_col = None
    collected = []          # [(posted_datetime, row)]
    seen = set()
    for n, (doc_id, post_dt) in enumerate(archives, 1):
        if n > HF_POSTINGS:
            break
        text = download_csv(auth, emil, doc_id)
        if not text:
            continue
        allrows = list(_csv.reader(io.StringIO(text)))
        if len(allrows) < 2:
            continue
        hdr, body = allrows[0], allrows[1:]
        if header is None:
            header, date_col = hdr, detect_any_date_column(hdr, body)
        for r in body:
            key = tuple(r)
            if key in seen:
                continue
            seen.add(key)
            collected.append((post_dt, r))

    if not collected:
        return {"emil": emil, "status": "empty", "rows": 0, "table": None}

    return _load_rolling(conn, emil, name, header, date_col, collected)


def _load_rolling(conn, emil, name, header, date_col, collected):
    """Shared tail for the rolling / latest loaders: keep every CSV column
    verbatim (any interval timestamp is preserved as text, not collapsed to a
    DATE) and add a derived `content_date` DATE for indexing/dedup, then reload
    just the content-dates present (idempotent). `collected` is [(post_dt, row)]."""
    types = infer_types(header, [r for _pd, r in collected])
    if date_col is not None:
        c, _t, _k = types[date_col]
        types[date_col] = (c, "varchar(32) DEFAULT NULL", "str")
    col_defs = [(c, t) for c, t, _ in types] + [("content_date", "date NOT NULL")]
    insert_names = ["posted_datetime"] + [c for c, _, _ in types] + ["content_date"]

    def content_date(r, post_dt):
        if date_col is not None and date_col < len(r):
            d = _parse_date(r[date_col])
            if d:
                return d.strftime("%Y-%m-%d")
        return post_dt.split(" ")[0]

    def build(post_dt, r):
        vals = [post_dt]
        for idx, (_c, _t, kind) in enumerate(types):
            raw = r[idx] if idx < len(r) else ""
            vals.append(coerce(kind, raw))
        vals.append(content_date(r, post_dt))
        return vals

    rows_values = [build(pd, r) for pd, r in collected]
    loaded_dates = sorted({v[-1] for v in rows_values})
    tbl = table_name(emil, name)
    _create_and_load(conn, tbl, col_defs, "content_date", insert_names,
                     rows_values, loaded_dates)
    return {"emil": emil, "status": "ok", "rows": len(collected),
            "table": tbl, "posted": collected[0][0]}


def _seed_latest(auth, conn, emil, name, last_post=None, lookback_days=45):
    """Create + load from the single newest available posting, whatever content-
    date it carries. For reports posted on a delay (60-day/2-day/3-day
    disclosures) or as-needed, where chasing a fixed target date fails —
    'most recent available data'. Scans postDatetime newest-first and loads the
    first non-empty posting. The window is anchored on the catalog's
    lastPostDatetime so dormant reports (last posted months ago) still resolve."""
    import csv as _csv
    today = datetime.now().date()
    ref = today
    if last_post:
        try:
            ref = min(today, datetime.strptime(last_post[:10], "%Y-%m-%d").date())
        except ValueError:
            pass
    dfrom = (ref - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    dto = (ref + timedelta(days=1)).strftime("%Y-%m-%d")
    archives = list_archives(auth, emil, dfrom, dto)
    if not archives:
        return {"emil": emil, "status": "no-archives", "rows": 0, "table": None}

    for n, (doc_id, post_dt) in enumerate(archives, 1):
        if n > MAX_DOWNLOADS:
            return {"emil": emil, "status": f"cap-{MAX_DOWNLOADS}-empty",
                    "rows": 0, "table": None}
        text = download_csv(auth, emil, doc_id)
        if not text:
            continue
        allrows = list(_csv.reader(io.StringIO(text)))
        if len(allrows) < 2:
            continue
        header, body = allrows[0], allrows[1:]
        date_col = detect_any_date_column(header, body)
        return _load_rolling(conn, emil, name, header, date_col,
                             [(post_dt, r) for r in body])

    return {"emil": emil, "status": "empty", "rows": 0, "table": None}


def seed_one(auth, conn, emil, name, target, high_freq=False):
    return (_seed_highfreq if high_freq else _seed_daily)(
        auth, conn, emil, name, target)


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


def _is_excluded(product):
    """RTD products are never listed, created, or seeded — excluded by posting
    frequency ("Per RTD Run") or by an "RTD" token in the report name."""
    freq = (product.get("generationFrequency") or "").lower()
    if any(m in freq for m in EXCLUDE_MARKERS):
        return True
    return bool(NAME_EXCLUDE_RE.search(product.get("name") or ""))


def main():
    ap = argparse.ArgumentParser(description="Seed stats_illustrator DATA-product tables.")
    ap.add_argument("emils", nargs="*", help="EMIL ids to seed (e.g. NP6-345-CD)")
    ap.add_argument("--date", help="content date to load (YYYY-MM-DD); "
                                   "required unless --latest")
    ap.add_argument("--latest", action="store_true",
                    help="ignore --date and load each report's most recent "
                         "available posting (for delayed / as-needed reports)")
    ap.add_argument("--pilot", action="store_true", help="seed the built-in pilot set")
    ap.add_argument("--delayed", action="store_true",
                    help="seed the built-in delayed set (disclosures / as-needed); "
                         "intended with --latest")
    ap.add_argument("--all", action="store_true",
                    help="seed every DATA product (all frequencies; RTD excluded)")
    ap.add_argument("--reseed-existing", action="store_true",
                    help="don't skip products that already have a table")
    args = ap.parse_args()
    if not args.latest and not args.date:
        ap.error("--date is required unless --latest is given")

    catalog = load_catalog()
    if args.all:
        emils = list(catalog.keys())
    elif args.delayed:
        emils = DELAYED
    elif args.pilot:
        emils = PILOT
    else:
        emils = args.emils
    if not emils:
        sys.exit("Nothing to do: pass EMIL ids, --pilot, --delayed, or --all.")

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
        if _is_excluded(p):
            print(f"{emil:<12} {'rtd-excluded':<20} "
                  f"({p.get('generationFrequency')})")
            results.append({"emil": emil, "status": "rtd-excluded", "rows": 0})
            continue
        if emil in CURATED_SKIP:
            print(f"{emil:<12} {'curated-skip':<20} (dedicated loader owns it)")
            results.append({"emil": emil, "status": "curated-skip", "rows": 0})
            continue
        # In the bulk --date pass, don't waste downloads on the delayed set — the
        # nightly `--latest --delayed` pass refreshes those instead.
        if args.all and not args.latest and emil in DELAYED:
            print(f"{emil:<12} {'delayed-skip':<20} (use --latest --delayed)")
            results.append({"emil": emil, "status": "delayed-skip", "rows": 0})
            continue
        if not args.reseed_existing and _has_table(stems, emil):
            print(f"{emil:<12} {'exists-skip':<20} (table already present)")
            results.append({"emil": emil, "status": "exists-skip", "rows": 0})
            continue
        try:
            if args.latest:
                res = _seed_latest(auth, conn, emil, p["name"],
                                   last_post=p.get("lastPostDatetime"))
            else:
                res = seed_one(auth, conn, emil, p["name"], args.date,
                               high_freq=_is_highfreq(p))
        except Exception as e:  # noqa: BLE001 — keep going through the batch
            res = {"emil": emil, "status": f"error: {e}", "rows": 0, "table": None}
        tag = res["status"]
        print(f"{emil:<12} {tag:<20} rows={res['rows']:<7} "
              f"{res.get('table') or ''}")
        results.append(res)

    conn.close()
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nSeeded {ok}/{len(results)} tables "
          + (f"(latest available)." if args.latest else f"for {args.date}."))


if __name__ == "__main__":
    main()
