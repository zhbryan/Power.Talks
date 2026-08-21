#!/usr/bin/env python3
"""
Deposit a visualization-ready snapshot of one ERCOT EMIL report under
Documents Database/STATS.ILLUSTRATOR/<emilId>/ for the static homepage to fetch.

Why a snapshot (not the whole archive): a report like NP3-560-CD holds 670k+
rows and grows hourly, but the illustrator only needs the *latest* posting (the
current 7-day forecast, a couple hundred rows). This pulls that slice, turns the
API's positional rows into objects using the report's own field schema, and
writes compact JSON that the React SPA can load directly — no database required.

Output (per Power.Talks conventions, fetched data -> Documents Database/):
  Documents Database/STATS.ILLUSTRATOR/<emilId>/
      meta.json      report metadata + field schema + source endpoint
      latest.json    the most recent posting: {postedDatetime, columns, rows[]}
      snapshots/<postedDatetime>.json   dated copy of each posting captured
      index.json     newest-first list of captured snapshots

Usage:
  py -3 "Database Codes/ercot_api/fetch_report_snapshot.py"                 # NP3-560-CD
  py -3 "Database Codes/ercot_api/fetch_report_snapshot.py" NP3-565-CD
"""

import json
import os
import sys

import requests

import list_emil_products as L   # reuse auth + credential loading

DEFAULT_EMIL = "NP3-560-CD"
CATALOG = os.path.join(L.OUT_DIR, "emil_products_latest.json")
STATS_DIR = os.path.join(L.PROJECT_ROOT, "Documents Database", "STATS.ILLUSTRATOR")
# The report's default sort is postedDatetime DESC, so a single first page holds
# the newest posting. 500 rows comfortably covers one posting (7 days x 24h + DST).
FIRST_PAGE_SIZE = 500


def endpoint_for(emil_id, headers):
    """Find the report's structured data endpoint from the saved catalog,
    falling back to a live self-lookup."""
    if os.path.exists(CATALOG):
        cat = json.load(open(CATALOG, encoding="utf-8"))
        for p in cat.get("products", []):
            if str(p.get("emilId")).lower() == emil_id.lower():
                arts = p.get("artifacts") or []
                if arts:
                    href = arts[0].get("_links", {}).get("endpoint", {}).get("href")
                    if href:
                        return href, p
    # Fallback: live metadata lookup.
    self_url = f"{L.REPORTS_URL}/{emil_id.lower()}"
    r = requests.get(self_url, headers=headers, timeout=30)
    r.raise_for_status()
    p = r.json()
    arts = p.get("artifacts") or []
    if arts:
        href = arts[0].get("_links", {}).get("endpoint", {}).get("href")
        if href:
            return href, p
    sys.exit(f"ERROR: no data endpoint found for {emil_id}")


def fetch_latest_posting(endpoint, headers):
    """Return (fields, rows_of_latest_posting, posted_datetime, total_records)."""
    r = requests.get(endpoint, headers=headers,
                     params={"page": 1, "size": FIRST_PAGE_SIZE}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"ERROR: data request failed ({r.status_code}): {r.text[:400]}")
    d = r.json()
    fields = d.get("fields") or []
    data = d.get("data") or []
    total = (d.get("_meta") or {}).get("totalRecords")
    names = [f["name"] for f in fields]
    # Column index of postedDatetime, so we can isolate the newest posting.
    try:
        pi = names.index("postedDatetime")
    except ValueError:
        pi = 0
    rows = [dict(zip(names, row)) for row in data]
    latest_ts = max((row[pi] for row in data), default=None)
    latest = [r for r in rows if r.get(names[pi]) == latest_ts]
    return fields, names, latest, latest_ts, total


def write_snapshot(emil_id, product, fields, names, rows, posted_ts, total):
    out = os.path.join(STATS_DIR, emil_id)
    snaps = os.path.join(out, "snapshots")
    os.makedirs(snaps, exist_ok=True)

    meta = {
        "emilId": emil_id,
        "name": product.get("name"),
        "description": product.get("description"),
        "reportTypeId": product.get("reportTypeId"),
        "generationFrequency": product.get("generationFrequency"),
        "sourceEndpoint": product.get("artifacts", [{}])[0]
            .get("_links", {}).get("endpoint", {}).get("href"),
        "totalRecordsAvailable": total,
        "fields": fields,   # the report's own schema (name/label/dataType)
    }
    snapshot = {
        "emilId": emil_id,
        "postedDatetime": posted_ts,
        "columns": names,
        "rowCount": len(rows),
        "rows": rows,
    }

    json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    json.dump(snapshot, open(os.path.join(out, "latest.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    safe = (posted_ts or "unknown").replace(":", "").replace("T", "_")
    json.dump(snapshot, open(os.path.join(snaps, f"{safe}.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    # Rebuild index (newest-first) from whatever snapshot files exist.
    entries = []
    for fn in os.listdir(snaps):
        if fn.endswith(".json"):
            entries.append(fn[:-5])
    entries.sort(reverse=True)
    index = {"emilId": emil_id, "name": product.get("name"),
             "snapshots": [{"postedKey": e, "file": f"snapshots/{e}.json"} for e in entries]}
    json.dump(index, open(os.path.join(out, "index.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    return out


def main():
    emil_id = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMIL).upper()
    user, pwd, key = L.load_credentials()
    print(f"Authenticating…")
    token = L.get_id_token(user, pwd)
    headers = {"Authorization": f"Bearer {token}", "Ocp-Apim-Subscription-Key": key}

    print(f"Resolving data endpoint for {emil_id}…")
    endpoint, product = endpoint_for(emil_id, headers)
    print(f"  {endpoint}")
    print("Fetching latest posting…")
    fields, names, rows, posted_ts, total = fetch_latest_posting(endpoint, headers)
    out = write_snapshot(emil_id, product, fields, names, rows, posted_ts, total)

    print(f"\n{emil_id} — {product.get('name')}")
    print(f"  latest posting : {posted_ts}")
    print(f"  rows captured  : {len(rows)}  (of {total:,} total in the archive)")
    print(f"  columns        : {', '.join(names)}")
    print(f"  deposited to   : {out}")


if __name__ == "__main__":
    main()
