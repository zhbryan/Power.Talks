---
name: Hot-Topics-Generator
description: Skill for producing the daily "ERCOT Hot Topics" report. Maintains a registry of information sources (ERCOT.com, recent stakeholder meetings, PUCT, top electricity-market news sites), summarizes each source's latest items, ranks the topics most frequently discussed across sources (ERCOT power market only), and writes a dated report under Documents Database/HOT.TOPICS/.
trigger: When the user asks to generate hot topics, a daily ERCOT news/topics report, "what's hot in the ERCOT market", to summarize recent ERCOT/PUCT/market news, or to run/update the Hot Topics report.
---

# ERCOT Hot Topics Generator

## What this produces

A dated report at:

```
Documents Database/HOT.TOPICS/<YYYY-MM-DD>/
    hot_topics_<YYYY-MM-DD>.md   ← the report (this is the deliverable)
    _prep.json                    ← machine input (sources + recent meetings)
    sources_checked.json          ← audit of what was actually pulled
```

One folder per day. The report summarizes every source, then ranks the topics
most frequently discussed across them — **scoped to the ERCOT power market only.**

## The information sources (maintained registry)

The source list lives in **`Database Codes/hot_topics/sources.json`** — edit that
file to add, remove, disable, or re-rank a source (do **not** hard-code sources
here). Enabled sources today:

1. **ERCOT.com** — Market Notices/Announcements and News/Press releases.
2. **Recent stakeholder meetings** — every ERCOT committee meeting whose dated
   folder on disk falls within the window (`within_days`, default 7). These are
   auto-discovered from `Documents Database/ERCOT.STKHDR.MEETS/` by the helper.
3. **PUCT** — the most recent Public Utility Commission of Texas open meeting
   (agenda, orders, rulemakings) plus Interchange filings when relevant.
4. **Five electricity-market news sites** — RTO Insider (ERCOT), Utility Dive,
   S&P Global Commodity Insights, POWER Magazine, Reuters Energy. Alternates
   (Texas Tribune, E&E Energywire) are in the registry, disabled, for swap-in.

## How to generate the report

### Step 1 — Scaffold + discover recent meetings (deterministic)

```bash
cd "E:\wamp64\www\Power.Talks"
py -3 "Database Codes/hot_topics/gen_hot_topics.py"            # today
py -3 "Database Codes/hot_topics/gen_hot_topics.py" --date 2026-07-30  # a specific day
```

This creates `Documents Database/HOT.TOPICS/<date>/`, writes `_prep.json` (enabled web sources +
stakeholder meetings found within the window + their document lists), and writes
a report skeleton. Read `_prep.json` — it is your worklist.

### Step 2 — Gather + summarize each source (AI: WebSearch / WebFetch)

Work only with items **published/updated within `within_days`** (default 7).
For each `web_source` in `_prep.json`:

- Prefer **WebFetch** on the source URL; use **WebSearch** (e.g.
  `RTO Insider ERCOT July 2026`) to surface the latest headlines, then fetch the
  specific articles.
- If a site is paywalled or empty, note it and enable an alternate from the
  registry rather than leaving a gap.
- Write a **2–4 sentence summary per item**: what happened, the ERCOT-market
  relevance, and any date/number/docket. Skip items with no ERCOT nexus.

For each meeting in `recent_meetings`: summarize from its documents on disk
(agenda, minutes, presentations at the listed `path`) — the key decisions,
revision requests discussed, and action items. Do not re-download; the files are
already there.

For **PUCT**: summarize the latest open-meeting agenda/orders and any open
rulemaking that touches ERCOT (market design, reliability, cost recovery, large
load, PCM).

### Step 3 — Rank the hot topics (ERCOT market only)

- Normalize mentions into a **canonical topic vocabulary** (see `ercot_market_focus`
  in `_prep.json`), e.g. *RTC+B*, *ECRS / ancillary services*, *ORDC & scarcity
  pricing*, *large loads / data centers*, *interconnection & GINR*, *transmission
  build-out (765 kV / CCN)*, *reserve margin / PCM*, *DER & aggregation*,
  *specific NPRR/NOGRR*, *weather & grid conditions*, *CRR / congestion*.
- **Count frequency = number of distinct sources** that mention each topic
  (not raw article count — cross-source corroboration is the signal).
- **Drop anything not tied to the ERCOT footprint** (e.g. PJM capacity auctions,
  California rooftop solar, national IRA news with no ERCOT angle).
- Rank descending; break ties by recency and by primary-source weight
  (ERCOT/PUCT official > news).

### Step 4 — Write the report

Overwrite `Documents Database/HOT.TOPICS/<date>/hot_topics_<date>.md` with:

1. **Title + date + scope line.**
2. **🔥 Top Hot Topics** — a ranked table: `# | Topic | Mentions | Sources |
   Why it matters (1 line)`. Aim for the top 8–12. Follow with a 2–3 sentence
   narrative on the single hottest theme.
3. **📋 Source Summaries** — grouped: ERCOT.com · Recent stakeholder meetings ·
   PUCT · News sites. Bullet the summarized items with links/paths.
4. **🗂️ Sources checked** — every source with status (pulled / empty / paywalled /
   swapped).

Then write **`sources_checked.json`** next to the report: for each source, the
`id`, `url`, `status`, item count, and newest item date — so a later run (or the
user) can audit coverage.

Keep the tone factual and tight — this is a market-intelligence brief, not prose.

## Running it daily

The report is meant to be produced once a day. Two ways to automate:

- **Scheduled Claude run** (recommended — the summarization needs the model):
  use the `/schedule` skill to run *this* skill each morning.
- The deterministic scaffold (Step 1) is headless-safe and can be added as a
  step in `Database Codes/run_routine.py` so the folder + `_prep.json` are ready
  before the AI pass. It does **not** call any API on its own.

## Maintaining the sources

- Edit `Database Codes/hot_topics/sources.json`. Toggle `enabled`, change `rank`,
  adjust `within_days`, or refine `ercot_market_focus` (the topic scope filter).
- To swap a paywalled news site, set its `enabled` to `false` and enable an
  alternate in `news_sites_alternates`.
- Stakeholder-meeting discovery needs no config — it reads whatever is on disk
  under `ERCOT.STKHDR.MEETS`. Run the ERCOT Stakeholder Meeting Downloader first
  if you want the very latest meeting materials included.

## Key files

| File | Purpose |
|------|---------|
| `Database Codes/hot_topics/sources.json` | The maintained source registry (edit this) |
| `Database Codes/hot_topics/gen_hot_topics.py` | Deterministic prep: scaffolds the dated folder, discovers recent meetings, writes `_prep.json` + skeleton |
| `Documents Database/HOT.TOPICS/<date>/hot_topics_<date>.md` | The daily report (deliverable) |
| `Documents Database/HOT.TOPICS/<date>/_prep.json` | Worklist for the AI step |
| `Documents Database/HOT.TOPICS/<date>/sources_checked.json` | Coverage audit written by the AI step |
