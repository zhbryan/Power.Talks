---
name: Set-Stats-Illustrator-Homepage
description: Build and maintain the "Stats Illustrator" section homepage on the Power.Talks website — the center view that shows a most-recent-day ERCOT market & grid dashboard (DAM vs SCED energy prices, DAM vs SCED ancillary-service MCPCs by type, load forecast vs actual vs available capacity, and top-20 DAM vs SCED congestion rents by constraint), plus the section's trimmed right panel. All chart data is read LIVE from the local MySQL "stats_illustrator" schema through its report tables, via a WAMP PHP endpoint; the charts are inline SVG. Covers the stats_dashboard.php endpoint and its queries, the StatsIllustratorHome component, the section route, and the Quick-runs panel changes.
trigger: When the user asks to create, change, or debug the Stats Illustrator section/homepage, its market/grid dashboard charts, the stats_dashboard.php data endpoint / its MySQL queries, or the Stats Illustrator right panel.
---

# Set Stats Illustrator Homepage

## What this is

The **Stats Illustrator** section (`activeSection === "stats-illustrated"`) renders
a **most-recent-day ERCOT market & grid dashboard** in the center pane, plus a
trimmed right panel. Read **Set-Power-Talks-Website-Framework** first (app shell,
bundle/rebuild pipeline, module contract, the right panel). This skill covers only
this section.

**All chart data comes LIVE from the local MySQL `stats_illustrator` schema**,
queried directly through its ERCOT report tables. The browser can't open a MySQL
connection, so a small **PHP endpoint on WAMP** runs the SQL on each request and
returns JSON — the page always reflects the current contents of the tables (no
snapshot, no generate step, no rebuild for data).

```
Browser ──fetch──► html/api/stats_dashboard.php ──mysqli──► stats_illustrator (MySQL)
   StatsIllustratorHome (illustration.jsx)  ◄──JSON──┘   renders 4 inline-SVG charts
```

WAMP = Apache + **MySQL** + **PHP**, so the database and a PHP runtime are already
present on `http://localhost/Power.Talks/…`. The endpoint reuses the same DB
credentials the Python tools use (`Database Codes/ercot_api/db_config.json`).

## Spec — the dashboard (main content panel)

Four charts for the **most recent delivery day available in the tables** — compute
it as the latest date present in *all four* datasets (the min of each dataset's max
date), so no chart is a day ahead of another:

| # | Chart | Type | Series |
|---|---|---|---|
| a | **DAM vs SCED energy prices** | dual line, x = hour 1–24, y = $/MWh | DAM system lambda vs SCED system lambda (hourly-averaged) |
| b | **DAM vs SCED ancillary-service MCPCs by type** | grouped bars, x = AS type, y = $/MW | DAM MCPC vs real-time MCPC, per type (REGUP, REGDN, RRS, ECRS, NSPIN) |
| c | **Load forecast vs actual load vs available capacity** | line, x = hour, y = MW | forecast, actual demand, available capacity — three series |
| d | **Top-20 DAM vs SCED congestion rents by constraint** | horizontal grouped bars, y = `fromStation → toStation`, x = $ | DAM rent vs SCED rent, `rent = shadowPrice × constraintValue` |

## Data source — the `stats_illustrator` tables

Every value is a `SELECT`/aggregate over these tables **in the `stats_illustrator`
schema**. Column names below are current — the endpoint should **re-inspect**
(`SHOW COLUMNS`) if a query errors; ERCOT report schemas drift. These tables are
seeded by the **ERCOT Public API - Daily Data Tables Update** pipeline.

**(a) Energy prices**
- DAM: `np4_523_cd_dam_system_lambda` — `deliverydate, hourending, systemlambda` (24 hourly points).
- SCED (real-time): `np6_322_cd_sced_system_lambda` — `scedtimestamp, cappedsystemlambda, content_date` (5-min). Average `cappedsystemlambda` per hour-ending to overlay on the DAM line.

**(b) AS MCPCs by type**
- DAM: `np4_188_cd_dam_clearing_prices_for_capacity` — `deliverydate, hourending, ancillarytype, mcpc`. Types: `REGUP, REGDN, RRS, ECRS, NSPIN`. Daily average `mcpc` per type.
- Real-time: `np6_331_cd_real_time_clearing_prices_for_capacity_b` — `astype, mcpc`, **filter on `content_date`** (its `deliverydate` is a raw `MM/DD/YYYY` varchar). Daily average per `astype`. (5-min alternative: `np6_332_…` — `scedtimestamp, astype, cappedmcpc`.)

**(c) Load forecast vs actual vs available capacity**
- Forecast: `np3_565_cd_seven_day_load_forecast_by_model_and_wea` — `deliverydate, hourending, systemtotal, model, inuseflag`. Use `systemtotal`, filtered to the operative model (`inuseflag = 'Y'`), for the target `deliverydate`.
- Actual: `np6_235_cd_system_wide_demand` — `deliverydate, timeending, demand` (system total).
- Available capacity: `np6_328_cd_total_capability_of_resources_available` — `scedtimestamp, capregup_rrs_ecrs_nspintotal, content_date` is real-time online **headroom** (available-but-not-deployed). Plot **available capacity ≈ actual demand + headroom** per hour (5-min → hourly avg). **This is an approximation** — confirm NP6-328's semantics and note it in the chart footnote.

**(d) Congestion rents** — `rent = shadowPrice × constraintValue`, summed over the day, grouped by `(fromStation, toStation)`, top 20 by rent.
- DAM: `np4_191_cd_dam_shadow_prices` — `deliverydate, hourending, shadowprice, constraintvalue, fromstation, tostation`. Rent per row = `shadowprice * constraintvalue` (hourly).
- SCED: `np6_86_cd_sced_shadow_prices_and_binding_transmiss` — `scedtimestamp, shadowprice, value, fromstation, tostation, content_date`. Rent per row = `shadowprice * value * (5/60)` to convert a 5-min interval to an hourly-equivalent so DAM and SCED sums compare. Note the unit reconciliation in SQL.
- Rank pairs by the larger of the two rents (or by DAM); show DAM and SCED bars side by side per pair. Exclude rows with a null/blank `fromstation` (unmapped system constraints) — they can't sit on a station→station axis.

### Schema gotchas (verified against the DB)

The seeder normalizes each report differently — these bit the first build:

- **Which date column to filter on.** Daily reports (`np4_523`, `np4_188`, `np4_191`, `np3_565`, `np6_235`) carry a real `deliverydate` DATE. High-frequency / SCED reports (`np6_322`, `np6_331`, `np6_328`, `np6_86`) carry a normalized **`content_date`** DATE — filter on that; their `deliverydate`/`scedtimestamp` are raw report fields.
- **Timestamps are varchars, not DATETIME.** `scedtimestamp` is `MM/DD/YYYY HH:MM:SS` and `timeending` is `HH:MM` text — `HOUR()` returns NULL on them. Parse first: `HOUR(STR_TO_DATE(scedtimestamp,'%m/%d/%Y %H:%i:%s'))+1`, `HOUR(STR_TO_DATE(timeending,'%H:%i'))+1`.
- **Real-time completeness is limited.** The high-frequency tables are seeded as small **rolling samples**, not full days: `np6_322`/`np6_328` hold ~24 rows/day (clustered, not one-per-hour) and `np6_235` ~3 rows/day. So DAM series render fully but **SCED intraday curves and the actual-load line are sparse** with the current seed. The endpoint returns `null` for missing hours (the component must tolerate gaps). Enriching the real-time seed to capture full days is a separate pipeline task; note the limitation in the chart footnotes.

## The PHP endpoint (live DB access)

Create `html/api/stats_dashboard.php`, served at
`http://localhost/Power.Talks/html/api/stats_dashboard.php`. It:

1. **Reads DB credentials from the shared config** — don't hard-code them:
   ```php
   $cfg = json_decode(file_get_contents(__DIR__ . '/../../Database Codes/ercot_api/db_config.json'), true);
   $db  = new mysqli($cfg['host'], $cfg['user'], $cfg['password'], $cfg['database'], (int)$cfg['port']);
   $db->set_charset('utf8mb4');
   ```
   (`db_config.json` = host `127.0.0.1`, port `3306`, user `root`, empty password,
   database `stats_illustrator` — the WAMP default the Python tools already use.)
2. Resolves the **target day** (max date common to (a)–(d); optional `?date=YYYY-MM-DD`
   override — bind it with a prepared statement).
3. Runs the four aggregations above with `SELECT`s (read-only; use prepared
   statements for the date param) and assembles the response.
4. Emits JSON with no-cache headers so the page is always live:
   ```php
   header('Content-Type: application/json');
   header('Cache-Control: no-store');
   echo json_encode($out);
   ```

Response shape (keep it chart-ready — the component should not aggregate):

```json
{
  "generated_at": "2026-09-23T…", "date": "2026-09-14",
  "energy_prices": { "hours":[1,…,24], "dam":[…], "sced":[…] },
  "as_mcpc":       { "types":["REGUP","REGDN","RRS","ECRS","NSPIN"], "dam":[…], "rt":[…] },
  "load_capacity": { "hours":[1,…,24], "forecast":[…], "actual":[…], "available":[…] },
  "congestion":    [ { "from":"…", "to":"…", "dam":123.4, "sced":98.7 }, … 20 ],
  "notes": { "available_capacity": "actual demand + online headroom (NP6-328)…" }
}
```

**Keep it read-only and self-contained**: only `SELECT`s against
`stats_illustrator`, no writes, no user input beyond an optional bound `date`. On a
DB/query error, return `{ "error": "…" }` with HTTP 500 so the component can show a
useful message. There is **no nightly generate step and no rebuild for data** — the
endpoint reads the tables live; the data is as current as the last seed run.

> Requires PHP's **mysqli** extension (default-on in WAMP). If the endpoint 500s
> with "Class mysqli not found", enable `php_mysqli` in WAMP's PHP config and
> restart Apache.

## The component

`StatsIllustratorHome` — **append it inside `html/src/illustration.jsx`** (exports
`window.StatsIllustratorHome`), same reasoning as `HotTopicsHome`:
`rebuild_standalone.py` only *updates* the 11 known entries, so reuse an existing
module rather than adding a `src/*.jsx` file (which would need a manifest + ANCHORS
entry and bump the count).

- Fetch `/Power.Talks/html/api/stats_dashboard.php` with `cache: "no-store"`.
  Handle `loading` / `error` (Apache/MySQL down, mysqli disabled, or a query error —
  surface the endpoint's `error` message and point the user at the tables /
  `db_config.json`) / `ready`, like the other homepages.
- **Charts are inline SVG** — the framework pins its CDN scripts and loads **no chart
  library or bundler**. Draw axes, gridlines, lines, and bars by hand in `<svg>`,
  sized with `viewBox` and scaled to the data's min/max. Theme with the site CSS
  vars (`--ink`, `--muted`, `--rule`, `--accent`, `--accent-2`, `--ok`, `--warn`,
  `--mono`, `--serif`); include a small legend per chart. Do **not** add
  Recharts/D3/Chart.js.
- Layout: a 2×2 responsive grid of chart cards with a header showing the data date.
  Chart (d) has long labels and 20 rows — give it its own full-width card and let it
  scroll inside an `overflow-x`/`overflow-y` container. The page body must never
  scroll horizontally.
- Header: title + the response `date` (e.g. "Most recent day — 2026-09-14").

Route it in `html/src/app.jsx`, in the `MessageStream` illustration switch:

```jsx
: activeSection === "stats-illustrated"
? <StatsIllustratorHome/>
```

`SECTION_LABELS["stats-illustrated"] = "Stats Illustrator"` already exists; the
sidebar and ERCOT-home Quick-Access card already link to `stats-illustrated`.

## Spec — the right panel (Quick runs)

Two changes in `html/src/rightpanel.jsx`, treating `stats-illustrated` like the
existing "no For-the-talk" sections (`isErcotHome`, `onMeetingTree`):

1. **Remove the "For the talk" tab** for this section, and force the Artifacts tab.
   - Add `const isStatsHome = ctx.section === "stats-illustrated";`
   - Add `!isStatsHome` alongside `!isErcotHome && !onMeetingTree` on the
     **tab button** render (the `"For the talk"` `<button>`) and on the
     **`tab === "runs"`** content block.
   - Add `isStatsHome` to the effect that forces `setTab("artifacts")`
     (currently `if (isErcotHome || onMeetingTree) setTab("artifacts")`).

2. **Trim the Artifacts list to exactly two** — "Write a briefing note" (`a3`) and
   "Summarise as a tweet thread" (`a7`) — removing all others for this section.
   - Add `const STATS_HOME_ARTIFACT_IDS = ["a3", "a7"];` near
     `ERCOT_HOME_ARTIFACTS` / `CATEGORY_HIDDEN_ARTIFACT_IDS`.
   - In `activeArtifacts`, add a branch:
     `isStatsHome ? allArtifacts.filter(a => STATS_HOME_ARTIFACT_IDS.includes(a.id)) : …`
     (filtering `ARTIFACTS` preserves DATA order, so `a3` then `a7`).

   The ids come from `data.jsx` `ARTIFACTS`: `a3` = *Write a briefing note*,
   `a7` = *Summarise as a tweet thread* (note ERCOT-site British spelling). If you
   want the American "Summarize", change the label in `data.jsx`, not here.

## Workflows

### Build / change the dashboard
1. Write/adjust `html/api/stats_dashboard.php`; test it directly (it's live):
   ```bash
   curl "http://localhost/Power.Talks/html/api/stats_dashboard.php" | head -c 800
   ```
   Confirm valid JSON with the four sections and a `date`.
2. Add/edit `StatsIllustratorHome` in `html/src/illustration.jsx`; route it in
   `app.jsx`; make the two `rightpanel.jsx` edits.
3. Rebuild the bundle — **must report 11 entries**:
   ```bash
   py -3 "html/rebuild_standalone.py"
   ```
4. Hard-refresh `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html`
   (Ctrl+F5) and **drive the real page**: open **Stats Illustrator** from the
   sidebar; verify the 4 charts render, the right panel shows **no "For the talk"
   tab** and exactly the two artifacts.

### Change the data
Edit the **SQL in `stats_dashboard.php`** (or seed a missing day into the tables) —
the page reflects it on the next load. **No rebuild** is needed for data, only for
the component. Freshness tracks the tables, which the nightly seed keeps current.

## Verifying

- `stats_dashboard.php` returns HTTP **200** and valid JSON at
  `http://localhost/Power.Talks/html/api/stats_dashboard.php`; the home page also 200s.
- The endpoint's `date` equals the latest day common to all four datasets; changing
  the tables (or passing `?date=`) changes the response with no redeploy.
- The served bundle contains the component: decode the `illustration.jsx` manifest
  entry and grep for `function StatsIllustratorHome` / `window.StatsIllustratorHome`,
  and the `app.jsx` entry for `<StatsIllustratorHome/>`.
- Right panel on this section: only the **Artifacts** tab; exactly **Write a briefing
  note** + **Summarise as a tweet thread**.
- Spot-check a number: run the same SQL in MySQL (e.g. one DAM `systemlambda` hour,
  or `SUM(shadowprice*constraintvalue)` for a top congestion pair) and compare to the
  endpoint's JSON.

## Common mistakes

| Mistake | Fix |
|---|---|
| Charts blank / "couldn't load" | Apache/MySQL down or the endpoint errored — open `stats_dashboard.php` directly, read its `error` |
| Endpoint 500 "Class mysqli not found" | Enable `php_mysqli` in WAMP's PHP config, restart Apache |
| Hard-coded DB password in PHP | Read `Database Codes/ercot_api/db_config.json` so credentials stay in one place |
| Tried to open a MySQL connection from the browser / JSX | Not possible — the browser calls the PHP endpoint, which runs the SQL |
| Added a chart library from a CDN | Framework loads no bundler/chart lib — draw inline SVG with CSS-var theming |
| Split the component into a new `src/*.jsx` | Keep it in `illustration.jsx`, or hand-add a manifest + ANCHORS entry (else rebuild < 11) |
| Edited component but page unchanged | Served page is a frozen bundle — `rebuild_standalone.py` then Ctrl+F5 (data needs no rebuild) |
| DAM and SCED prices/rents mismatched in scale | Reconcile units in SQL: SCED is 5-min — average prices to hourly; multiply 5-min rents by 5/60 before summing |
| One chart is a day ahead of another | Target the max date **common to all four** datasets; SCED tables key on `content_date`, DAM on `deliverydate` |
| Missing a day in a source table | Backfill it (`seed_data_product_tables.py --date <d> <EMIL> --reseed-existing`) — see the daily-tables skill |
| SQL injection via `?date=` | Bind it with a prepared statement; keep the endpoint SELECT-only |

## Related skills

- **Set-Power-Talks-Website-Framework** — app shell, bundle pipeline, module
  contract, right panel.
- **ERCOT Public API - Daily Data Tables Update** — how the `stats_illustrator`
  tables (this dashboard's live source) are seeded/refreshed.
- **Set-ERCOT-Homepage** — the `market-home` view whose Quick-Access grid links into
  this section, and the model for a section with no "For the talk" tab.
