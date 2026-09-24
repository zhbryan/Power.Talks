---
name: ERCOT-Market-Keywords-Updater
description: Refresh the curated list of key words / topics popularly discussed and studied in the ERCOT (Texas) wholesale electricity market. Unlike the ERCOT Glossary (a verbatim scrape of ercot.com/glossary definitions), this list is judgment-curated from live research — ERCOT stakeholder-meeting agendas, recent revision requests, PUCT actions, and analyst/trade commentary — capturing what the market is actually talking about, with the currently-trending items flagged. Maintains a Markdown source plus a JSON companion under Database Codes/reference_info/.
trigger: When the user asks to update/refresh/rebuild the ERCOT market keyword or hot-topic list, add new market terms/topics, refresh what's "trending" in the ERCOT wholesale market, or regenerate ercot_market_keywords.md / .json.
---

# ERCOT Market Keywords Updater

Maintains a living, categorized list of the terms and topics **popularly discussed
and studied** in the ERCOT wholesale market — the market's *conversation*, as
opposed to the formal definitions in `ERCOT_Glossary.md`.

## Files (reference material → `Database Codes/reference_info/`)

```
Database Codes/reference_info/
    ercot_market_keywords.md      ← AUTHORED source of truth (human-readable, categorized)
    ercot_market_keywords.json    ← generated companion (machine-readable)
    build_keywords_json.py        ← deterministic .md → .json converter
```

The **`.md` is the source of truth** — you edit it. The `.json` is *always*
regenerated from it by the script; never hand-edit the JSON.

## This is a curation task, not a scrape

The glossary updater fetches one page and extracts an array. This list has no
single source — it reflects editorial judgment about what is *prominent*. So the
refresh is a research-and-merge workflow you (Claude) perform:

### 1. Read the current list
Open `ercot_market_keywords.md` (categories, bullets, and the 🔥 Trending table)
and note the existing `Compiled:` date so you know how stale it is.

### 2. Research what's current
Use `WebSearch` / `WebFetch`, prioritizing recent (last ~6–12 months) signals:
- **ERCOT stakeholder activity** — TAC/board/working-group agendas & presentations
  (ercot.com/committees, ercot.com/calendar), new **NPRR/NOGRR/other revision
  requests**, market notices. The project already tracks these — cross-check
  recent titles under `Documents Database/ERCOT.MKT.RULES/` and
  `Documents Database/ERCOT.STKHDR.MEETS/`, and any recent
  `Documents Database/HOT.TOPICS/` reports.
- **PUCT** — open meetings, rulemakings, legislation (SB/HB) affecting ERCOT.
- **Analyst / trade coverage** — Modo Energy, Enverus, Ascend, Utility Dive, RBN,
  law-firm alerts — for what practitioners are focused on.
Capture source URLs as you go; they go in the **Sources** section.

### 3. Update the Markdown
- **🔥 Trending now table** — the most important edit. Add newly-hot topics; demote
  ones that have cooled (move them from the table down into their thematic
  section, keep the bullet). Keep it to ~8–12 rows with a one-line "why it's hot".
- **Thematic sections** — add new keywords to the right category as
  `- **Term (ACRONYM)** — one-line description`. Retire only genuinely obsolete
  terms; historical-but-quiet terms can stay (they're still "studied").
- **Quick-reference acronyms** — add any new acronyms to the inline list.
- **Header** — bump `- **Compiled:** YYYY-MM-DD` to today.
- **Sources** — add/refresh the links you used.

### 4. Regenerate the JSON companion
```bash
cd "E:\wamp64\www\Power.Talks"
py -3 "Database Codes/reference_info/build_keywords_json.py"          # build + report
py -3 "Database Codes/reference_info/build_keywords_json.py" --quiet  # headless
```
It prints `N keywords across C categories, T flagged trending`. Sanity-check that
N and T moved in the direction you expect.

## Markdown format contract (the parser depends on this)

`build_keywords_json.py` parses the `.md` structurally — keep these shapes intact:

| Element | Shape | Parsed as |
|---|---|---|
| Compiled date | `- **Compiled:** 2026-09-23` | `compiled_at` |
| Category heading | `## 3. Scarcity pricing & reliability economics` | a `category` (leading `N.` stripped) |
| Keyword bullet | `- **Term (ACR)** — description` | `{term, acronym, category, description}` |
| Trending row | `\| **Label (ACR)** \| why \|` under the `🔥 Trending now` heading | sets `trending: true` on matching keywords |
| Non-category headings | anything containing `Trending now`, `Quick-reference acronyms`, or `Sources` | skipped (not a category) |

Trending is matched to a keyword by its acronym or a distinctive phrase from the
table label, so **spell the trending label consistently** with its section bullet
(e.g. include the acronym in parentheses) and the flag propagates automatically.

## JSON schema

```json
{
  "source": "...", "compiled_at": "YYYY-MM-DD",
  "count": 86, "trending_count": 12,
  "categories": ["Market design & structure", "..."],
  "keywords": [
    {"term": "Locational Marginal Price (LMP)", "acronym": "LMP",
     "category": "Market design & structure",
     "description": "nodal price = energy + congestion + loss components",
     "trending": false}
  ]
}
```

## Cadence & automation

On-demand / periodic (e.g. monthly, or whenever the market shifts) — **not** wired
into the 2 AM `run_routine.py` refresh, because the content needs editorial
judgment, not a deterministic scrape. If you want it automated, run it like the
Hot Topics fill: a headless `claude.exe -p` job that performs steps 1–4 and is
registered as its own scheduled task. The JSON build (step 4) is pure-stdlib
Python; the research (step 2) needs web access.

## Notes

- Keep it **distinct from the glossary**: this file lists *topics people discuss*,
  the glossary lists *official definitions*. A term can appear in both.
- Prefer concise, plain-English one-liners over protocol language.
- Related: `ERCOT Glossary Updater` (definitions), `Hot Topics Generator` (daily
  brief — a natural consumer of the trending set).
