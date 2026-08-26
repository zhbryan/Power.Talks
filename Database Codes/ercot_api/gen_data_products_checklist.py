#!/usr/bin/env python3
"""gen_data_products_checklist.py — table-build checklist for ERCOT DATA products.

Reads the EMIL product catalog (written by list_emil_products.py), keeps the
products whose contentType is "DATA" (the row-structured reports that map to
relational tables), and labels each one with whether a matching table already
exists in the `stats_illustrator` MySQL schema.

Output (per Power.Talks conventions, generated data -> Documents Database/):
  Documents Database/ERCOT.PUBAPI/data_products_table_checklist_<YYYY-MM-DD>.csv
  Documents Database/ERCOT.PUBAPI/data_products_table_checklist_latest.csv

Columns: #, emilId, reportTypeId, name, in_database, existing_table

DB-optional: if pymysql is missing or MySQL is unreachable, the checklist is
still written (in_database left blank, existing_table = "<db-unavailable>"), so
a scheduled run never fails just because the database is down.

DB config (env-var overrides, same names as backfill_report_archive.py):
  STATS_DB_HOST (127.0.0.1)  STATS_DB_USER (root)  STATS_DB_PASSWORD ("")
  STATS_DB_NAME (stats_illustrator)  STATS_DB_PORT (3306)

Usage:
  py -3 "Database Codes/ercot_api/gen_data_products_checklist.py"
  py -3 "Database Codes/ercot_api/gen_data_products_checklist.py" --quiet
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(PROJECT_ROOT, "Documents Database", "ERCOT.PUBAPI")
LATEST_JSON = os.path.join(OUT_DIR, "emil_products_latest.json")


def _db_config():
    return {
        "host": os.environ.get("STATS_DB_HOST", "127.0.0.1"),
        "user": os.environ.get("STATS_DB_USER", "root"),
        "password": os.environ.get("STATS_DB_PASSWORD", ""),
        "database": os.environ.get("STATS_DB_NAME", "stats_illustrator"),
        "port": int(os.environ.get("STATS_DB_PORT", "3306")),
    }


CHECKLIST_TABLE = "data_products_table_checklist"

CHECKLIST_DDL = f"""
CREATE TABLE IF NOT EXISTS `{CHECKLIST_TABLE}` (
  `date_refresh` date NOT NULL,
  `emil_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `report_type_id` int DEFAULT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `in_database` tinyint(1) NOT NULL DEFAULT '0',
  `existing_table` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loaded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`date_refresh`,`emil_id`),
  KEY `idx_emil` (`emil_id`),
  KEY `idx_in_database` (`in_database`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def get_connection():
    """Open a MySQL connection, or return None if the DB can't be reached
    (pymysql missing / server down). Callers degrade gracefully on None."""
    try:
        import pymysql
    except ImportError:
        print("WARN: pymysql not installed — writing checklist without DB labels/table.")
        return None
    cfg = _db_config()
    try:
        return pymysql.connect(
            host=cfg["host"], user=cfg["user"], password=cfg["password"],
            database=cfg["database"], port=cfg["port"], connect_timeout=10,
            autocommit=False)
    except Exception as e:  # noqa: BLE001 — any connect failure => degrade gracefully
        print(f"WARN: could not reach MySQL ({e}) — writing checklist without DB labels/table.")
        return None


def existing_tables(conn):
    """Return the set of table names in the stats schema for the given conn."""
    cfg = _db_config()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=%s", (cfg["database"],))
        return {r[0] for r in cur.fetchall()}


def write_checklist_table(conn, rows, date_refresh):
    """Create (if needed) and upsert the checklist snapshot for date_refresh."""
    with conn.cursor() as cur:
        cur.execute(CHECKLIST_DDL)
        cur.execute(
            f"DELETE FROM `{CHECKLIST_TABLE}` WHERE date_refresh=%s", (date_refresh,))
        cur.executemany(
            f"INSERT INTO `{CHECKLIST_TABLE}` "
            "(date_refresh, emil_id, report_type_id, name, in_database, existing_table) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            [(date_refresh, r["emilId"], r["reportTypeId"], r["name"],
              1 if r["in_database"] == "YES" else 0,
              r["existing_table"] or None) for r in rows])
    conn.commit()


def _norm(emil):
    """EMIL id -> the table-name stem convention (lowercase, dashes -> _)."""
    return str(emil).lower().replace("-", "_")


def _match_table(emil, tables):
    """Find an existing table whose name starts with the EMIL id stem.
    e.g. NP3-560-CD -> np3_560_cd -> np3_560_cd_7d_load_fcast_by_fzn."""
    stem = _norm(emil)
    for t in sorted(tables):
        if t == stem or t.startswith(stem + "_"):
            return t
    return ""


def load_data_products():
    if not os.path.exists(LATEST_JSON):
        sys.exit(f"ERROR: {LATEST_JSON} not found. Run list_emil_products.py first.")
    with open(LATEST_JSON, encoding="utf-8") as f:
        doc = json.load(f)
    products = doc.get("products", [])
    data = [p for p in products if p.get("contentType") == "DATA"]
    data.sort(key=lambda p: (str(p.get("reportTypeId")), str(p.get("emilId"))))
    return data


def main():
    ap = argparse.ArgumentParser(description="Refresh the DATA-products table checklist.")
    ap.add_argument("--quiet", action="store_true", help="suppress per-row output")
    ap.add_argument("--date-refresh", default=datetime.now().strftime("%Y-%m-%d"),
                    help="DATE_REFRESH stamp for the DB checklist table "
                         "(YYYY-MM-DD; default today)")
    args = ap.parse_args()

    data = load_data_products()
    conn = get_connection()
    db_ok = conn is not None
    tables = existing_tables(conn) if db_ok else set()

    rows = []
    for i, p in enumerate(data, 1):
        emil = p.get("emilId")
        tbl = _match_table(emil, tables) if db_ok else ""
        rows.append({
            "#": i,
            "emilId": emil,
            "reportTypeId": p.get("reportTypeId"),
            "name": p.get("name"),
            "in_database": "YES" if tbl else ("" if db_ok else ""),
            "existing_table": tbl if db_ok else "<db-unavailable>",
        })

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    dated = os.path.join(OUT_DIR, f"data_products_table_checklist_{stamp}.csv")
    latest = os.path.join(OUT_DIR, "data_products_table_checklist_latest.csv")
    fields = ["#", "emilId", "reportTypeId", "name", "in_database", "existing_table"]
    for path in (dated, latest):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    # Persist the snapshot into the DB checklist table (stamped DATE_REFRESH).
    if db_ok:
        try:
            write_checklist_table(conn, rows, args.date_refresh)
            print(f"DB checklist table `{CHECKLIST_TABLE}` updated for "
                  f"date_refresh={args.date_refresh} ({len(rows)} rows).")
        except Exception as e:  # noqa: BLE001 — never let a DB hiccup fail the CSV refresh
            print(f"WARN: could not write `{CHECKLIST_TABLE}` ({e}).")
        finally:
            conn.close()

    existing = sum(1 for r in rows if r["in_database"] == "YES")
    print(f"DATA products: {len(rows)}"
          + (f"  |  in DB: {existing}  |  to build: {len(rows) - existing}"
             if db_ok else "  |  DB unavailable (labels blank)"))
    if not args.quiet and db_ok:
        for r in rows:
            if r["in_database"] == "YES":
                print(f"  EXISTS -> {r['emilId']} | {r['name']} | {r['existing_table']}")
    print(f"Saved:\n  {dated}\n  {latest}")


if __name__ == "__main__":
    main()
