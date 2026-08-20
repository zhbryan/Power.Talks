---
name: ERCOT-Public-API-List-EMIL-Products
description: List every available EMIL (ERCOT Market Information List) data product from the ERCOT Public API. Authenticates against ERCOT's Azure B2C, walks the full product catalog at api.ercot.com/api/public-reports, and writes the complete list (EMIL ID, name, Report Type ID) to Documents Database/ERCOT.PUBAPI/. Use when the user wants the ERCOT data-product catalog, all EMIL products, or a machine-readable list of ERCOT public reports.
trigger: When the user asks to list ERCOT EMIL products, enumerate ERCOT public data products/reports, pull the ERCOT data-product catalog, or refresh the list of available ERCOT Public API reports.
---

# ERCOT Public API — List EMIL Products

Developer docs: <https://apiexplorer.ercot.com/> · <https://developer.ercot.com/applications/pubapi/user-guide/using-api/>

## What this produces

The complete ERCOT **EMIL** catalog. EMIL ("ERCOT Market Information List") is
ERCOT's list of every public data product it is required to publish. Each
product carries an **EMIL ID** (e.g. `NP4-159-CD`) and a numeric **Report Type
ID** (e.g. `12324`); those IDs are what you use to pull the actual data from
`.../api/public-reports/{emilId}/{endpoint}`.

Output (fetched data → `Documents Database/`, per project conventions):

```
Documents Database/ERCOT.PUBAPI/
    emil_products_<YYYY-MM-DD>.json   ← full records, dated
    emil_products_<YYYY-MM-DD>.csv    ← flat table: emilId, name, reportTypeId, reportType
    emil_products_latest.json         ← stable copy (overwritten each run)
```

## How the API works

| | |
|---|---|
| Catalog endpoint | `GET https://api.ercot.com/api/public-reports` |
| Auth token (ROPC) | `POST https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token` |
| Required headers | `Authorization: Bearer <id_token>` **and** `Ocp-Apim-Subscription-Key: <subscription_key>` |
| Token lifetime | ~1 hour, **no refresh** — request a new one each run |

Every request needs **both** the Bearer token and the subscription key; missing
either returns 401. Report URLs are **lowercase** — an uppercase EMIL ID in a
path returns 404 (the catalog listing itself is unaffected).

## One-time setup: credentials

You need an ERCOT Public API account (register at the API Explorer) which gives
you a **username/password** and a **subscription key** (API Explorer → your
profile → Products → *Show* the Primary key).

Provide them either way:

- **File** (preferred): copy `Database Codes/ercot_api/ercot_api_credentials.example.json`
  to `ercot_api_credentials.json` in the same folder and fill it in. That real
  file is **gitignored**.
- **Environment**: set `ERCOT_API_USERNAME`, `ERCOT_API_PASSWORD`,
  `ERCOT_API_SUBSCRIPTION_KEY`.

The user must supply their own credentials — never hard-code or commit them.

## How to run

```bash
cd "E:\wamp64\www\Power.Talks"
py -3 "Database Codes/ercot_api/list_emil_products.py"           # prints table + saves files
py -3 "Database Codes/ercot_api/list_emil_products.py" --quiet   # save only, no per-row output
```

The script (`Database Codes/ercot_api/list_emil_products.py`):

1. Loads credentials (file → env fallback).
2. Gets an ID token via the B2C ROPC password grant.
3. GETs `/api/public-reports`, paging through every page until the catalog is
   exhausted (uses `_meta.totalPages` when present, else stops on a short page).
4. Normalizes each record to `emilId / name / reportTypeId / reportType`,
   sorts by EMIL ID, and writes the JSON + CSV outputs above.

## Notes & troubleshooting

- **`AADB2C90225: username or password invalid`** on the token call → wrong
  credentials (the endpoint/flow itself is correct).
- **401 on the catalog call** → missing/expired token or wrong subscription key.
- **Could not locate product records** → the response shape changed; the script
  dumps the raw first page to `Documents Database/ERCOT.PUBAPI/_raw_public_reports_page1.json`
  so the parser (`_extract_products`) can be adjusted.
- Uses only `requests` (already installed). No other dependencies.
- To consume the result elsewhere, read `emil_products_latest.json` — its
  `products` array holds the full raw records, not just the flattened columns.
