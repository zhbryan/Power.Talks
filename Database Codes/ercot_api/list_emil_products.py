#!/usr/bin/env python3
"""
List every available EMIL product from the ERCOT Public API.

EMIL = ERCOT Market Information List: the catalog of public data products
(each identified by an EMIL ID like "NP4-159-CD" and a numeric Report Type ID).
The Public API exposes the catalog at the top-level reports endpoint; this
script authenticates, walks every page, and writes the full product list.

Docs (as of 2026-08):
  Base API   : https://api.ercot.com/api/public-reports
  Auth (ROPC): https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/
               B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token
  Every request needs BOTH:
    Authorization: Bearer <id_token>      (valid 1 hour, no refresh -> re-fetch)
    Ocp-Apim-Subscription-Key: <sub_key>  (API Explorer profile -> Products)

Credentials are read from (first that exists):
  1. Database Codes/ercot_api/ercot_api_credentials.json   (gitignored)
  2. Environment: ERCOT_API_USERNAME / ERCOT_API_PASSWORD / ERCOT_API_SUBSCRIPTION_KEY

Output (per Power.Talks conventions, fetched data -> Documents Database/):
  Documents Database/ERCOT.PUBAPI/emil_products_<YYYY-MM-DD>.json  (full records)
  Documents Database/ERCOT.PUBAPI/emil_products_<YYYY-MM-DD>.csv   (flat table)
  Documents Database/ERCOT.PUBAPI/emil_products_latest.json        (stable copy)

Usage:
  py -3 "Database Codes/ercot_api/list_emil_products.py"
  py -3 "Database Codes/ercot_api/list_emil_products.py" --quiet   # no per-row print
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import requests

# --- Constants ---------------------------------------------------------------

TOKEN_URL = ("https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/"
             "B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token")
CLIENT_ID = "fec253ea-0d06-4272-a5e6-b478baeecd70"
SCOPE = f"openid {CLIENT_ID} offline_access"
REPORTS_URL = "https://api.ercot.com/api/public-reports"

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_DIR = os.path.join(PROJECT_ROOT, "Documents Database", "ERCOT.PUBAPI")
CRED_FILE = os.path.join(HERE, "ercot_api_credentials.json")

PAGE_SIZE = 1000  # ask for large pages; the API caps and paginates as needed


# --- Credentials -------------------------------------------------------------

def load_credentials():
    """Return (username, password, subscription_key). File wins over env."""
    if os.path.exists(CRED_FILE):
        with open(CRED_FILE, encoding="utf-8") as f:
            c = json.load(f)
        user = c.get("username")
        pwd = c.get("password")
        key = c.get("subscription_key")
    else:
        user = os.environ.get("ERCOT_API_USERNAME")
        pwd = os.environ.get("ERCOT_API_PASSWORD")
        key = os.environ.get("ERCOT_API_SUBSCRIPTION_KEY")
    missing = [n for n, v in (("username", user), ("password", pwd),
                              ("subscription_key", key)) if not v]
    if missing:
        sys.exit(
            "ERROR: missing credential(s): " + ", ".join(missing) + ".\n"
            f"Create {CRED_FILE} (see ercot_api_credentials.example.json) or set "
            "ERCOT_API_USERNAME / ERCOT_API_PASSWORD / ERCOT_API_SUBSCRIPTION_KEY."
        )
    return user, pwd, key


# --- Auth --------------------------------------------------------------------

def get_id_token(username, password):
    """ROPC password grant -> ID token (Bearer). Valid ~1h, no refresh."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "scope": SCOPE,
            "response_type": "id_token",
            "username": username,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"ERROR: token request failed ({resp.status_code}): {resp.text[:500]}")
    tok = resp.json()
    # ROPC with response_type=id_token returns the JWT under id_token (older
    # tenants echo it as access_token) — accept either.
    token = tok.get("id_token") or tok.get("access_token")
    if not token:
        sys.exit(f"ERROR: no id_token in token response: {list(tok.keys())}")
    return token


# --- Catalog fetch -----------------------------------------------------------

def _extract_products(payload):
    """Pull the product list out of a page payload, tolerant of shape.
    Returns a list of dicts. ERCOT returns HAL JSON: the catalog lives under
    _embedded.products. Also accept a few other shapes / a bare list."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        emb = payload.get("_embedded")
        if isinstance(emb, dict):
            v = emb.get("products")
            if isinstance(v, list):
                return v
            for v in emb.values():        # first list inside _embedded
                if isinstance(v, list):
                    return v
        for key in ("products", "data", "reports", "items", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                return v
        # Fallback: first list of dicts among the top-level values.
        for v in payload.values():
            if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                return v
    return []


def _next_link(payload):
    """HAL next-page URL, if the response advertises one."""
    if isinstance(payload, dict):
        nxt = (payload.get("_links") or {}).get("next")
        if isinstance(nxt, dict):
            return nxt.get("href")
        if isinstance(nxt, str):
            return nxt
    return None


def fetch_all_products(token, subscription_key, quiet=False):
    """Walk every page of the top-level reports endpoint. Returns list of dicts."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }
    products, page = [], 1
    url, params = REPORTS_URL, {"page": 1, "size": PAGE_SIZE}
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        if resp.status_code != 200:
            sys.exit(f"ERROR: reports request failed on page {page} "
                     f"({resp.status_code}): {resp.text[:500]}")
        payload = resp.json()
        batch = _extract_products(payload)
        if not batch:
            if page == 1:
                # Nothing parsed — dump raw so the shape can be inspected.
                raw = os.path.join(OUT_DIR, "_raw_public_reports_page1.json")
                os.makedirs(OUT_DIR, exist_ok=True)
                with open(raw, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                sys.exit("ERROR: could not locate product records in the response. "
                         f"Raw payload written to {raw} for inspection.")
            break
        products.extend(batch)
        if not quiet:
            print(f"  page {page}: +{len(batch)} (total {len(products)})")
        # ERCOT paginates via a HAL 'next' link; absent -> single/last page.
        nxt = _next_link(payload)
        if not nxt:
            break
        url, params, page = nxt, None, page + 1
    return products


# --- Normalization / output --------------------------------------------------

def _first(d, *keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return ""


def normalize(products):
    """Flatten each product to the fields users care about, keeping the rest."""
    rows = []
    for p in products:
        if not isinstance(p, dict):
            continue
        rows.append({
            "emilId": _first(p, "emilId", "emil_id", "EMILId", "id"),
            "name": _first(p, "name", "reportName", "productName", "title"),
            "reportTypeId": _first(p, "reportTypeId", "report_type_id", "reportTypeID"),
            "reportType": _first(p, "reportType", "report_type", "type"),
        })
    rows.sort(key=lambda r: str(r["emilId"]).lower())
    return rows


def write_outputs(products, rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    doc = {
        "source": REPORTS_URL,
        "retrieved": datetime.now().isoformat(timespec="seconds"),
        "count": len(products),
        "products": products,   # full raw records, for downstream use
    }
    dated_json = os.path.join(OUT_DIR, f"emil_products_{stamp}.json")
    latest_json = os.path.join(OUT_DIR, "emil_products_latest.json")
    dated_csv = os.path.join(OUT_DIR, f"emil_products_{stamp}.csv")
    for path in (dated_json, latest_json):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
    with open(dated_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["emilId", "name", "reportTypeId", "reportType"])
        w.writeheader()
        w.writerows(rows)
    return dated_json, dated_csv


# --- Main --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="List all ERCOT EMIL products.")
    ap.add_argument("--quiet", action="store_true", help="suppress per-row/page output")
    args = ap.parse_args()

    user, pwd, key = load_credentials()
    print("Authenticating with ERCOT B2C...")
    token = get_id_token(user, pwd)
    print("Fetching EMIL product catalog...")
    products = fetch_all_products(token, key, quiet=args.quiet)
    rows = normalize(products)

    dated_json, dated_csv = write_outputs(products, rows)
    print(f"\nRetrieved {len(products)} EMIL products.")
    if not args.quiet:
        print(f"{'EMIL ID':<16} {'Report Type':<12} Name")
        print("-" * 72)
        for r in rows:
            print(f"{str(r['emilId']):<16} {str(r['reportTypeId']):<12} {r['name']}")
    print(f"\nSaved:\n  {dated_json}\n  {dated_csv}")


if __name__ == "__main__":
    main()
