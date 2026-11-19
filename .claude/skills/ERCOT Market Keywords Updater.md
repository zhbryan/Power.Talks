---
name: ERCOT-Market-Keywords-Updater
description: Refresh the curated list of key words / topics popularly discussed and studied in the ERCOT (Texas) wholesale electricity market. Unlike the ERCOT Glossary (a verbatim scrape of ercot.com/glossary definitions), this list is judgment-curated from live research — ERCOT stakeholder-meeting agendas, recent revision requests, PUCT actions, and analyst/trade commentary — capturing what the market is actually talking about, with the currently-trending items flagged. Maintains a validated YAML vocabulary plus a JSON companion under Database Codes/reference_info/.
trigger: When the user asks to update/refresh/rebuild the ERCOT market keyword or hot-topic list, add new market terms/topics, refresh what's "trending" in the ERCOT wholesale market, or regenerate the ERCOT keyword vocabulary (ercot_keyword_vocabulary.yaml / .json).
---

# ERCOT Market Keywords Updater

Maintains a living, categorized list of the terms and topics **popularly discussed
and studied** in the ERCOT wholesale market — the market's *conversation*, as
opposed to the formal definitions in `ERCOT_Glossary.md`.

## Files (reference material → `Database Codes/reference_info/`)

```
Database Codes/reference_info/
    ercot_keyword_vocabulary.yaml ← AUTHORED source of truth (concepts + aliases)
    validate_vocabulary.py        ← enforces the three laws; run before anything else
    build_keywords_json.py        ← deterministic .yaml → .json build
    ercot_market_keywords.json    ← generated companion (machine-readable)
    ercot_market_keywords.md      ← narrative only; NOT machine-read since 2026-11-19
    propose_keywords.py           ← what the gallery needs that the vocabulary lacks
```

The **`.yaml` is the source of truth** — you edit it. The `.json` is *always*
regenerated from it; never hand-edit the JSON. The `.md` is now a human-facing
essay about the market conversation: keep it readable if you like, but editing
it changes nothing downstream.

## The three laws (enforced — `validate_vocabulary.py` fails the build)

1. **Generic only.** A concept names a recurring idea, never one instance of it:
   no bill numbers, revision-request numbers, years, months, MW thresholds or
   named projects. Rejected terms go in the YAML's `rejected:` block *with a
   reason*, so nobody re-adds them by accident.
2. **One concept, one term.** No term joins two ideas with `/` or `,`. Every
   alias must mean the same thing as its concept.
3. **No overlap.** No term's words contain another's (declare `broader:` if the
   relation is real hierarchy), no surface form is claimed twice, and no two
   concepts may tag substantially the same charts.

Every concept carries `glossary_ref` citing ERCOT's own glossary, **or** an
`extension_reason` saying why the glossary has no entry — it lags the market by
years and has nothing for ECRS, co-optimization or curtailment.

## After any edit, run the chain

```
py -3 "Database Codes/reference_info/validate_vocabulary.py"
py -3 "Database Codes/reference_info/build_keywords_json.py"
py -3 "Database Codes/sync_keyword_ids.py"
py -3 "Database Codes/download_GALLERY_charts/retag_charts.py" --dry-run   # review
py -3 "Database Codes/download_GALLERY_charts/retag_charts.py"
```

`retag_charts.py` re-applies the vocabulary to every chart already in the
gallery from stored text — no workbook is reopened, no AI call is spent — and
prints a per-concept diff. Always read the `--dry-run` diff before applying.
The nightly routine runs this whole chain as steps 38–42.

## Growing the vocabulary

Do not invent terms to fill gaps. `propose_keywords.py` ranks the phrases that
recur across untagged charts and that no concept matches; promote one by hand
with a scope note, a glossary citation (or a stated reason) and aliases. A
vocabulary that grows itself grows redundant.

## This is a curation task, not a scrape

The glossary updater fetches one page and extracts an array. This list has no
single source — it reflects editorial judgment about what is *prominent*. So the
refresh is a research-and-merge workflow you (Claude) perform:

### 1. Read the current list
Open `ercot_keyword_vocabulary.yaml` (concepts, aliases, `rejected:`) and note
the `compiled:` date so you know how stale it is. Check `propose_keywords.py`
output for gaps the corpus has already proven.

### 2. Research what's current
Use `WebSearch` / `WebFetch`, prioritizing recent (last ~6–12 months) signals:
- **ERCOT stakeholder activity** — TAC/board/working-group agendas & presentations
  (ercot.com/committees, ercot.com/calendar), new **NPRR/NOGRR/other revision
  requests**, market notices. The project already tracks these — cross-check
  recent titles under `Documents Database/ERCOT.MKT.RULES/` and
  `Documents Database/ERCOT.STKHDR.MEETS/`.
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
judgment, not a deterministic scrape. If you want it automated, run it as a
headless `claude.exe -p` job that performs steps 1–4, registered as its own
scheduled task. The JSON build (step 4) is pure-stdlib
Python; the research (step 2) needs web access.

## Notes

- Keep it **distinct from the glossary**: this file lists *topics people discuss*,
  the glossary lists *official definitions*. A term can appear in both.
- Prefer concise, plain-English one-liners over protocol language.
- Related: `ERCOT Glossary Updater` (definitions).
