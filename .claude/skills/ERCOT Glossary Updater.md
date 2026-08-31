---
name: ERCOT-Glossary-Updater
description: Build and refresh a living glossary document of ERCOT / power-system, grid, and market-operations terminology, sourced from ercot.com/glossary. The public glossary page is JavaScript-rendered — its A-Z letter links just filter one array embedded inline in the page (`glossaryData`), so the updater fetches that single page, extracts every term + definition, converts the HTML definitions to clean text, and writes an A-Z Markdown doc plus a JSON companion under Database Codes/reference_info/. Runs nightly in the 2 AM refresh.
trigger: When the user asks to build/update/refresh the ERCOT glossary, get ERCOT or power-system/grid/market terminology or definitions, scrape ercot.com/glossary, or regenerate the glossary reference document.
---

# ERCOT Glossary Updater

Maintains a single, versioned glossary of ERCOT power-system, grid, and
market-operations terms under `Database Codes/reference_info/`, refreshed from
ERCOT's official glossary.

## Source & why it's a single fetch

Source: <https://www.ercot.com/glossary>

The page looks like it has per-letter pages (A, B, C … links), but those links
are **client-side filters** (`glossaryPage.filterGlossary(...)`), not separate
URLs — every letter points at `#`. All ~700 terms are embedded **inline** in the
page HTML as a JSON array:

```js
glossaryData = [
  { "term_s": "ACE", "definition_html_raw": "<p>Area Control Error</p>" },
  ...
];
```

So the updater fetches the one page, pulls that array out with
`json.JSONDecoder().raw_decode` (robust to brackets inside the HTML), converts
each `definition_html_raw` fragment to clean multi-line text, and writes the doc.
**No per-letter crawling is needed or possible.**

## Outputs (reference material → `Database Codes/reference_info/`)

```
Database Codes/reference_info/
    ERCOT_Glossary.md      ← human-readable, A-Z grouped, one **term** + definition each
    ercot_glossary.json    ← machine-readable: {source, retrieved_at, count, terms[]}
```

`ERCOT_Glossary.md` header carries the source URL, term count, and last-updated
date. Both files are **overwritten** each run (a living document). When the JSON
already exists, the run prints a change summary — `N terms | +A added | -R
removed | ~C changed`.

## How to run

```bash
cd "E:\wamp64\www\Power.Talks"
py -3 "Database Codes/reference_info/update_ercot_glossary.py"          # build + report
py -3 "Database Codes/reference_info/update_ercot_glossary.py" --quiet  # nightly mode
```

Dependencies: `requests` only (already installed). No DB, no auth.

## Nightly automation

Wired into `run_routine.py` as the **REFERENCE** step (full runs only, i.e. not
`--only market` / `--only stkhdr`), so it refreshes with the 2 AM
**"Power.Talks Daily Refresh"** task. No separate scheduled task is needed.

## Notes & troubleshooting

- **`'glossaryData' not found` / JSON parse error** → ERCOT changed the page
  structure. The script dumps the raw page to
  `Database Codes/reference_info/_glossary_raw.html` so the extractor
  (`extract_glossary`) can be adjusted; inspect it for the new data shape.
- Definitions are HTML (`<p>`, `<ul><li>`, `<br>`, links). `html_to_text` turns
  paragraphs/line breaks into newlines and `<li>` into `- ` bullets, strips the
  rest, and unescapes entities — so multi-part definitions (e.g. **Outage** with
  Forced/Maintenance/Planned sub-definitions) stay readable.
- Terms are grouped by first letter (`## A` … `## Z`; non-alphabetic under `#`)
  and sorted case-insensitively.
- To consume the glossary elsewhere, read `ercot_glossary.json` — its `terms`
  array holds `{term_s, definition_html_raw}` verbatim.
