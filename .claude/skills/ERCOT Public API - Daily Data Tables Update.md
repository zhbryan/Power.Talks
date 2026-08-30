---
name: ERCOT-Public-API-Daily-Data-Tables-Update
description: Daily maintenance of the stats_illustrator MySQL database that mirrors ERCOT EMIL DATA products. Refreshes the product catalog, creates a table for every DATA product across all posting frequencies (5-minute, 15-minute, hourly, daily, per-SCED, per-DAM/RUC run — RTD products excluded), uploads the latest day's rows into each table (idempotent), and rebuilds the DATA-products -> table checklist. Wired into the 2 AM "Power.Talks Daily Refresh" scheduled run.
trigger: When the user asks to update/refresh the ERCOT data tables, create tables for ERCOT DATA products, upload the latest ERCOT report data to MySQL, refresh stats_illustrator, or run/repair the daily ERCOT table build. Also when re-assessing which EMIL DATA products do or don't have a database table.
---

# ERCOT Public API — Daily Data Tables Update

Keeps the `stats_illustrator` MySQL schema in step with the ERCOT EMIL **DATA**
product catalog: one relational table per report, kept current with the latest
day's postings. Runs every night as part of the 2 AM refresh, and can be run by
hand for a repair or a one-off date.

## What "DATA products" are

The EMIL catalog (`Documents Database/ERCOT.PUBAPI/emil_products_latest.json`,
written by the *List EMIL Products* skill) tags each product with a
`contentType`. The **`DATA`** ones are the row-structured CSV reports that map
cleanly to SQL tables; the rest (reports, notices) are out of scope here.

## Scope decisions baked into the scripts

- **All frequencies are seeded** — from `Chron - 5 Minutes` and
  `Chron - 15 Minutes` up through `Chron - Hourly` and `Chron - Daily`, plus the
  event-driven `Event - Per SCED Run` / `Per DAM Run` / `Per HRUC/DRUC/WRUC Run`
  reports.
- **RTD products are excluded entirely.** A product is treated as RTD — never
  listed, never given a table — if its `generationFrequency` is
  `Event - Per RTD Run` (`NP6-325-CD`, `NP6-329-CD`) **or** its `name` contains
  an `RTD` token (`NP6-970-CD` "RTD Indicative LMPs", which posts on a 5-minute
  chron). The rule lives in `_is_excluded` (`EXCLUDE_MARKERS` + `NAME_EXCLUDE_RE`)
  in `seed_data_product_tables.py` and in the matching `_rtd()` filter in
  `gen_data_products_checklist.py` — keep the two in agreement.

## The two loaders (why sub-hourly is different)

`seed_data_product_tables.py` picks a path per product:

| Path | Applies to | How it loads |
|------|-----------|--------------|
| **daily** (`_seed_daily`) | daily / hourly / event reports | One posting holds the whole content day. It finds the newest posting containing `--date`, keys the table on that report's own DATE column, and reloads just that content-date. |
| **high-freq** (`_seed_highfreq`) | 5-min, 15-min, per-SCED (`HIGHFREQ_MARKERS`) | These post a small slice every few minutes, so chasing a specific past day would blow the download budget. It ingests the **newest `HF_POSTINGS` (24) postings** — the current rolling window — keeps every column verbatim (the interval timestamp is preserved as text so sub-hour resolution survives), and adds a derived `content_date` DATE for indexing/dedup. |

Both paths are **idempotent**: they DELETE the content-date(s) they're about to
load before inserting, so re-running never duplicates rows. Tables use a
surrogate `id` PK (report natural keys differ), a `posted_datetime` column from
the archive posting, `loaded_at`, and an index on the content-date column.

> Note on high-freq coverage: a nightly high-freq run captures roughly the last
> ~2 hours of 5-minute data (24 postings), not a full historical day. That's a
> deliberate bound to keep the nightly job fast. For a full historical backfill
> of one report, use `backfill_report_archive.py` (as done for NP3-560-CD).

## The daily job (three steps, in order)

These run automatically inside `Database Codes/run_routine.py` on a full run
(the ERCOT PUBLIC API block), between the market/stakeholder tracks and the web
rebuild:

1. **Refresh the catalog** — `list_emil_products.py --quiet`
   rewrites `emil_products_{<date>,latest}.json/csv`.
2. **Seed / upload tables** — `seed_data_product_tables.py --date <yesterday>
   --all --reseed-existing`. `--all` covers every DATA product (RTD excluded);
   `--reseed-existing` makes it both **create** missing tables and **upload**
   the new day into tables that already exist. `<yesterday>` is computed in
   `run_routine.py` as the most recently complete content day. The **delayed
   set** (see below) is skipped here (`delayed-skip`) so this pass doesn't waste
   downloads failing on reports that never publish yesterday's data.
3. **Refresh the delayed set** — `seed_data_product_tables.py --latest --delayed
   --reseed-existing` reloads the disclosure / correction / as-needed reports
   from each one's most recent available posting.
4. **Rebuild the checklist** — `gen_data_products_checklist.py --quiet` rewrites
   `data_products_table_checklist_{<date>,latest}.csv` and upserts the
   `data_products_table_checklist` DB snapshot, labelling each product's
   `in_database` / `existing_table`.

This job is registered under the Windows task **"Power.Talks Daily Refresh"**
(2 AM) via `run_routine.py`; no separate task is needed.

### Backfill lock

The seed steps yield to a running historical backfill so the two don't fight over
the same tables and the ERCOT rate limit. `backfill_all_reports.py` writes
`Documents Database/STATS.ILLUSTRATOR/_backfill.lock` (refreshing its mtime as it
works); any `seed_data_product_tables.py` run sees a **fresh** lock and skips with
a message. A lock older than `LOCK_STALE_SECONDS` (30 min) means the backfill
died and is ignored automatically. Force a seed through with
`--ignore-backfill-lock`.

## Run it by hand

```bash
cd "E:\wamp64\www\Power.Talks\Database Codes\ercot_api"

# Nightly-equivalent: create missing + upload yesterday into all tables
py -3 seed_data_product_tables.py --date 2026-08-27 --all --reseed-existing

# Create only the tables that don't exist yet (skip the ones already built)
py -3 seed_data_product_tables.py --date 2026-08-27 --all

# One specific report
py -3 seed_data_product_tables.py --date 2026-08-27 NP6-345-CD

# Most-recent-available data, ignoring --date (for delayed / as-needed reports:
# 60-day / 2-day / 3-day disclosures, "Event - As Needed"). Loads each report's
# newest posting whatever content-date it carries.
py -3 seed_data_product_tables.py --latest --reseed-existing NP3-966-ER NP1-302

# Re-assess coverage (which DATA products have / lack a table)
py -3 gen_data_products_checklist.py
```

Per-row statuses: `ok`, `exists-skip` (already built, no `--reseed-existing`),
`rtd-excluded`, `curated-skip` (hand-maintained, e.g. NP3-560-CD), `no-archives`,
`date-not-found` (daily path found no posting with that content-date in the
window), `empty`, `not-data`.

### `--date` vs `--latest`

- `--date` (daily/high-freq loaders) is what the nightly run uses — it targets a
  specific content day (yesterday). It fails (`date-not-found`) for reports that
  don't publish that day's data on that day: the 60-day/2-day/3-day disclosures
  and `Event - As Needed` reports.
- `--latest` sidesteps that: it loads each report's newest available posting
  regardless of date (window anchored on the catalog's `lastPostDatetime`, so
  dormant reports still resolve). Use it to (re)build those delayed/as-needed
  tables.

The delayed reports are enumerated in the built-in **`DELAYED`** set
(`seed_data_product_tables.py`), selectable with **`--delayed`**. The nightly
run refreshes them with a dedicated `--latest --delayed --reseed-existing` pass;
the `--all --date` pass skips them (`delayed-skip`). If a new report only builds
via `--latest`, add its EMIL id to `DELAYED`.

```bash
# Refresh the whole delayed set from most-recent postings (nightly-equivalent)
py -3 seed_data_product_tables.py --latest --delayed --reseed-existing
```

## DB config

Env-var overrides (same names across all three scripts), defaults in
`db_config.json`:

```
STATS_DB_HOST (127.0.0.1)  STATS_DB_USER (root)  STATS_DB_PASSWORD ("")
STATS_DB_NAME (stats_illustrator)  STATS_DB_PORT (3306)
```

Credentials for the ERCOT API come from `ercot_api_credentials.json` (gitignored)
or the `ERCOT_API_*` env vars — see the *List EMIL Products* skill.

## Troubleshooting

- **`date-not-found` on a daily report** → the target date isn't in any posting
  in the `[-8, +1]` day window (report posted late, or the date is too old).
  Try a more recent `--date`, or widen `WINDOW_BEFORE`.
- **A high-freq table only has ~2 hours of data** → expected; see the coverage
  note above. Raise `HF_POSTINGS` for a wider nightly window, or backfill.
- **`cap-60-no-match`** (daily path) → the report's date column isn't being
  detected; check the CSV header and the hints in `DATE_HEADER_HINTS`.
- **DB unreachable** → the checklist step degrades gracefully (writes the CSV
  with blank labels); the seed step will error for that product but the batch
  continues. Start WAMP/MySQL and re-run.
- Uses `requests` + `pymysql` (both already installed).
