---
name: Set-Stats-Illustrator-Homepage
description: Build and maintain the "Stats Illustrator" section homepage on the Power.Talks website — the center view that shows a most-recent-day ERCOT market & grid dashboard as four full-width charts (DAM vs SCED settlement-point prices at HB_BUSAVG; ancillary-service MCPCs as one sub-chart per type, DAM-hourly vs SCED-interval; actual load stacked by forecast zone with the day-ahead forecast overlaid; and top-20 congestion rents shown as DAM and SCED side-by-side), plus the section's trimmed right panel. All chart data is read LIVE from the local MySQL "stats_illustrator" schema through its report tables, via a WAMP PHP endpoint; the charts are inline SVG. Covers the stats_dashboard.php endpoint and its queries, the StatsIllustratorHome component, the section route, and the Quick-runs panel changes.
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

Four charts for the **most recent delivery day** (target day = latest `deliverydate`
common to the DAM anchor tables; real-time overlays fill in where their tables have
that day). **Each chart spans the full width of the content panel** — they stack
vertically, one section each, not a 2×2 grid.

| # | Chart | Layout | Series |
|---|---|---|---|
| a | **DAM vs SCED settlement-point prices** at `HB_BUSAVG` | full-width dual line, x = hour of day, y = $/MWh | DAM **hourly** SPP vs SCED **15-min interval** SPP, both at settlement point `HB_BUSAVG` |
| b | **Ancillary-service MCPCs by type** | full-width **small-multiples — one sub-chart per AS type** (REGUP, REGDN, RRS, ECRS, NSPIN) | in each sub-chart: DAM **hourly** MCPC vs SCED **real-time interval** MCPC |
| c | **Load by forecast zone vs day-ahead forecast** | full-width — **stacked bars** over hours + a forecast line | actual system load **stacked by forecast zone** (North/South/West/Houston; stack total = system-wide demand) with the **day-ahead load forecast** overlaid |
| d | **Top-20 congestion rents** | full-width — **two charts side by side** (DAM \| SCED) | each an independent top-20 horizontal bar of `SUM(shadowPrice × constraintValue)` by `fromStation → toStation`; DAM from NP4-191, SCED from NP6-86 |

## Data source — the `stats_illustrator` tables

Every value is a `SELECT`/aggregate over these tables **in the `stats_illustrator`
schema**. Column names below are current — the endpoint should **re-inspect**
(`SHOW COLUMNS`) if a query errors; ERCOT report schemas drift. These tables are
seeded by the **ERCOT Public API - Daily Data Tables Update** pipeline.

**(a) Settlement-point prices at `HB_BUSAVG`** — mind the different column name per table.
- DAM (hourly): `np4_190_cd_dam_settlement_point_prices` — `deliverydate, hourending, settlementpoint, settlementpointprice`. Filter `settlementpoint = 'HB_BUSAVG'` and `deliverydate = ?` → 24 hourly points.
- SCED (15-min interval): `np6_905_cd_settlement_point_prices_at_resource_node` — `content_date, deliveryhour, deliveryinterval, settlementpointname, settlementpointprice`. Filter `settlementpointname = 'HB_BUSAVG'` and `content_date = ?`. Plot each interval; x = fractional hour-ending `= (deliveryhour - 1) + deliveryinterval/4`.

**(b) AS MCPCs by type (one sub-chart per type)**
- DAM (hourly): `np4_188_cd_dam_clearing_prices_for_capacity` — `deliverydate, hourending, ancillarytype, mcpc`. Per `ancillarytype`, an hourly series (24), `deliverydate = ?`.
- SCED (interval): `np6_331_cd_real_time_clearing_prices_for_capacity_b` — `content_date, deliveryhour, deliveryinterval, astype, mcpc`. Per `astype`, an interval series; **filter on `content_date`** (its `deliverydate` is a raw `MM/DD/YYYY` varchar). (5-min alternative: `np6_332_…` — `scedtimestamp, astype, cappedmcpc`.)
- Types: `REGUP, REGDN, RRS, ECRS, NSPIN` — five sub-charts, each DAM-hourly vs SCED-interval.

**(c) Actual load by forecast zone + day-ahead forecast**
- Actual by zone (stacked bars): `np6_346_cd_actual_system_load_by_forecast_zone` — `operday, hourending, north, south, west, houston, total`. Filter `operday = ?`; stack `north, south, west, houston` per hour (their sum = `total` = system-wide demand).
- Day-ahead forecast (line): `gen_55_cd_hourly_real_time_load_vs_actual_report` — `deliverydate, hourending, dayaheadforecast` (also has `actualload`, `currentdayforecast`). Filter `deliverydate = ?`, use `dayaheadforecast`.

**(d) Congestion rents — DAM and SCED computed independently** (two side-by-side top-20 lists). `rent = shadowPrice × constraintValue`, summed over the day, grouped by `(fromStation, toStation)`, top 20 by rent. Exclude rows with a null/blank `fromstation` (unmapped system constraints — no station→station axis).
- DAM: `np4_191_cd_dam_shadow_prices` — `deliverydate, hourending, shadowprice, constraintvalue, fromstation, tostation`. Rent per row = `shadowprice * constraintvalue`, filter `deliverydate = ?`.
- SCED: `np6_86_cd_sced_shadow_prices_and_binding_transmiss` — `content_date, shadowprice, value, fromstation, tostation`. Rent per row = `shadowprice * value * (5/60)` (5-min → hourly-equivalent), filter `content_date = ?`.

### Schema gotchas (verified against the DB)

The seeder normalizes each report differently — these bit the first build:

- **Which date column to filter on.** Daily reports (`np4_190`, `np4_188`, `np4_191`, `gen_55_cd_…`) carry a real `deliverydate` DATE; `np6_346` uses `operday` (DATE). Real-time reports (`np6_905`, `np6_331`, `np6_86`) carry a normalized **`content_date`** DATE — filter on that; their `deliverydate`/`deliveryhour`/`scedtimestamp` are raw report fields.
- **Settlement-point column name differs by table.** DAM `np4_190` uses **`settlementpoint`**; real-time `np6_905` uses **`settlementpointname`**. Both hold `HB_BUSAVG`.
- **Real-time interval math.** `np6_905` / `np6_331` express time as `deliveryhour` (1–24) + `deliveryinterval` (1–4 for 15-min); fractional hour-ending = `(deliveryhour - 1) + deliveryinterval/4`. `np6_86`'s `scedtimestamp` is `MM/DD/YYYY HH:MM:SS` varchar — parse with `STR_TO_DATE(...,'%m/%d/%Y %H:%i:%s')` if you need its hour (congestion only needs the date filter + sum).
- **Real-time / zone completeness is limited.** Several real-time tables are seeded as partial rolling samples, and `np6_346` (actual load by forecast zone) currently lags the DAM tables (its latest `operday` is earlier). So DAM series render fully but **SCED overlays and the stacked-zone bars can be sparse or absent** on the newest day. The endpoint returns `null` for missing points; the component must tolerate gaps and empty series. Pass `?date=` to view an older, fuller day. Enriching the seed is a separate pipeline task.

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
2. Resolves the **target day** = latest `deliverydate` common to the DAM anchor
   tables (`np4_190`, `np4_188`, `np4_191`, `gen_55_cd_…`); real-time and zone
   overlays use that same day where present. Optional `?date=YYYY-MM-DD` override —
   bind it with a prepared statement.
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
  "generated_at": "2026-09-24T…", "date": "2026-09-14",
  "prices_hub": {
    "point": "HB_BUSAVG",
    "dam":  { "hours":[1,…,24], "price":[…24] },
    "sced": { "x":[0.25,0.5,…,24], "price":[…] }          // 15-min interval points
  },
  "as_mcpc": {
    "types": ["REGUP","REGDN","RRS","ECRS","NSPIN"],
    "series": {                                            // one entry per type
      "REGUP": { "dam_hours":[1,…,24], "dam":[…], "rt_x":[…], "rt":[…] }
    }
  },
  "load_zone": {
    "hours": [1,…,24],
    "zones": ["North","South","West","Houston"],
    "stacks": { "North":[…24], "South":[…], "West":[…], "Houston":[…] },
    "forecast": [ …24 ]                                    // gen_55 dayaheadforecast
  },
  "congestion": {
    "dam":  [ { "from":"…", "to":"…", "rent":123.4 }, … 20 ],
    "sced": [ { "from":"…", "to":"…", "rent":98.7 }, … 20 ]
  }
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
- Layout: **each chart is its own full-width card**, stacked vertically (no 2×2 grid),
  with a header showing the data date. Per chart:
  - **(a) prices** — one wide dual-line chart; DAM as a 24-point hourly line, SCED as
    a denser 15-min line/points on the same fractional-hour x-axis.
  - **(b) AS MCPCs** — a **row of five small-multiple sub-charts** (one per type,
    responsive `grid` that wraps), each a mini DAM-vs-SCED line with the type as its
    title; share a single legend for the card.
  - **(c) load** — **stacked bars** per hour (one stack segment per forecast zone,
    distinct colors) with the day-ahead **forecast** drawn as a line on top.
  - **(d) congestion** — **two sub-charts side by side** (`grid` 2-col, wrapping to
    stacked on narrow), DAM (NP4-191) left and SCED (NP6-86) right, each a top-20
    horizontal bar with `from → to` labels; each scrolls inside its own
    `overflow` box. The page body must never scroll horizontally.
- Header: title + the response `date` (e.g. "Most recent day — 2026-09-14").
- Tolerate empty/partial series: a sub-chart or the SCED side may have no rows for
  the newest day — render a small "no data" placeholder rather than a broken axis.

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
- Spot-check a number: run the same SQL in MySQL (e.g. one DAM `settlementpointprice`
  hour at `HB_BUSAVG`, or `SUM(shadowprice*constraintvalue)` for a top DAM congestion
  pair) and compare to the endpoint's JSON.

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
| Wrong settlement-point column | DAM `np4_190` = `settlementpoint`; RT `np6_905` = `settlementpointname`. Both filter `HB_BUSAVG` |
| SCED congestion rents dwarf/undershoot DAM | Multiply 5-min SCED rents by `5/60` (hourly-equivalent) before summing; DAM is already hourly |
| Chart mixes days / real-time day empty | Target the latest `deliverydate` on the DAM anchors; RT (`content_date`) and zone (`operday`) tables may lag — render their gaps, or pass `?date=` |
| AS sub-chart or zone bars blank | That type/day has no rows — show a "no data" placeholder, don't break the axis |
| Missing a day in a source table | Backfill it (`seed_data_product_tables.py --date <d> <EMIL> --reseed-existing`) — see the daily-tables skill |
| SQL injection via `?date=` | Bind it with a prepared statement; keep the endpoint SELECT-only |

## Related skills

- **Set-Power-Talks-Website-Framework** — app shell, bundle pipeline, module
  contract, right panel.
- **ERCOT Public API - Daily Data Tables Update** — how the `stats_illustrator`
  tables (this dashboard's live source) are seeded/refreshed.
- **Set-ERCOT-Homepage** — the `market-home` view whose Quick-Access grid links into
  this section, and the model for a section with no "For the talk" tab.
