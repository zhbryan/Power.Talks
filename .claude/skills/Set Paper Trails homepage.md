---
name: Set-Paper-Trails-Homepage
description: Use when asked to set up, update, refresh, or extend the Paper Trails homepage in the Power.Talks web app — category list pages (NPRR, SCR, COPMGRR, NOGRR, PGRR, RMGRR), detail views, the Quick runs right panel, or adding a new market rules category to the UI.
trigger: When the user asks to update the Paper Trails homepage, refresh the rule lists shown on the webpage, make the homepage reflect new downloads/profiles/summaries, or add a category homepage to the web UI.
---

# Set Paper Trails Homepage

## Overview

Paper Trails is the market-rules section of the Power.Talks web app. It shows a
3×2 grid of category cards (NPRR, SCR, COPMGRR, NOGRR, PGRR, RMGRR); each card
opens a category homepage with status lists (Pending / Approved / Withdrawn /
Rejected), each issue opens a detail view (Summary) in the center pane and a
"Quick runs" profile card in the right panel.

Open via **http://localhost/Power.Talks/html/Power.Talks%20home%20page.html** —
never `file://`, because issue data is fetched from the WAMP server at runtime.

## File Map

| File | Role |
|---|---|
| `html/Power.Talks home page.html` | **Standalone bundle** served to the browser. All `src/*.jsx` files are embedded gzip+base64 in a `__bundler/manifest` script tag. Source edits do NOT appear until rebundled. |
| `html/rebuild_standalone.py` | Re-embeds every `src/*.jsx` into the bundle (matches entries by content fingerprint / anchor strings). Run after any src edit. Writes a `.bak` backup. |
| `html/src/app.jsx` | Top-level state: `activeSection` (`"paper-trails"`), `activePaperCode`, and one `active<Cat>` state + click handler per category. Passes `context={{ section, code, nprr, copmgrr, pgrr, scr, nogrr, rmgrr }}` to `RightPanel`. |
| `html/src/data.jsx` | **Static list data**: `const <CAT>_<STATUS> = [ { n, title }, ... ]` arrays, exported via `window.DATA`. This is what the category homepages list. |
| `html/src/illustration.jsx` | `PaperTrailsIllustration`: category grid (`PAPER_TRAIL_CODES`, exported as `window.PAPER_TRAIL_CODES`), per-category homepage list panels, and per-category `<Cat>DetailView` that fetches the issue's `Summary.json`. |
| `html/src/rightpanel.jsx` | "Quick runs" cards shown in the right panel per selected issue: `<Cat>ProfileCard` / `<Cat>SummaryCard`. Contains the `asList()` normalizer for profile schema differences. |

## Data Sources — two kinds

### 1. Static list arrays (must be regenerated when lists change)

`data.jsx` holds one array per category+status, ending in:

```js
window.DATA = { ..., NPRR_PENDING, NPRR_WITHDRAWN, NPRR_APPROVED,
  COPMGRR_PENDING, COPMGRR_WITHDRAWN, COPMGRR_APPROVED,
  PGRR_PENDING, PGRR_WITHDRAWN, PGRR_APPROVED,
  SCR_APPROVED, SCR_WITHDRAWN, SCR_REJECTED,
  NOGRR_PENDING, NOGRR_APPROVED, NOGRR_WITHDRAWN, NOGRR_REJECTED,
  RMGRR_PENDING, RMGRR_APPROVED, RMGRR_WITHDRAWN, ... };
```

Entry format: `{ n: 1329, title: "Resource Entity Requirements for Self-Limiting Facilities" }`.
Lists are sorted descending by issue number. Statuses come from each issue's
`Profile.json`; titles from `Summary.json`/`Profile.json`.

To regenerate after a downloader/profile run:

```bash
python "html/regen_paper_trails_data.py"   # rewrites all <CAT>_<STATUS> arrays in data.jsx in place
python "html/rebuild_standalone.py"        # re-embeds src into the served bundle
```

The regen script reads each issue's `Profile.json` (status, title — title
falls back to `Summary.json`), buckets by status, and replaces only arrays
that already exist in `data.jsx` (it warns about non-empty buckets with no
array). Titles have `"` replaced with `'`.

Also update the `count` in `PAPER_TRAIL_CODES` (in `illustration.jsx`) if a
category's total changes materially.

### 2. Live per-issue fetches (no rebuild needed — just regenerate the JSONs)

All URLs are relative to the WAMP docroot; spaces are %-encoded:

```
/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/Quick%20runs/<ISSUE_ID>%20Profile.json
/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/Quick%20runs/<ISSUE_ID>%20Summary.json
/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/<original document>   ← download target
```

| View | Fetches |
|---|---|
| Center detail view (`illustration.jsx`) | `Summary.json` (issue summary) **and** `Profile.json` (its `source_documents` for the Documents Submitted section) |
| Center **Document Summary view** (`illustration.jsx`) | nothing — renders the clicked `source_documents` entry passed via `activeRuleDoc` |
| Right panel Quick runs (`rightpanel.jsx`) | `Profile.json` for NPRR, COPMGRR, PGRR; `Summary.json` for SCR, NOGRR, RMGRR (no document list — it lives in the center) |

## Documents Submitted + per-document report (both panels)

**1. Documents Submitted section** — a `DocumentsSubmittedSection({ cat,
issueId, onDocClick })` rendered in every `<Cat>DetailView` (center) **below
Current Status**. It fetches the issue `Profile.json`, reads `source_documents`
(`.zip` excluded), and **sorts by the sequence number after `[rule#][CAT]-`**
(e.g. `1340NPRR-01` → 1; regex `^\d+[a-z]+[-_ ]+(\d+)`). Each row: a **title
link** showing the document's **Title Name** (entry `title`; filename stem with
`-`/`_`→spaces, UI fallback derives it from `file`) + a **download button**
(`<a download href={download_url}>`, `e.stopPropagation()`).

**2. Per-document report — opens in BOTH panels.** Clicking a title calls
`onDocClick(doc, issueId, cat)` → `onRuleDocClick` in `app.jsx`, which sets
`activeRuleDoc = {...doc, issueId, cat}`. That state is passed to **both**
`PaperTrailsIllustration` (as `ruleDoc`) **and** the `RightPanel` context (as
`ctx.ruleDoc`). An effect clears it when the section/category/selected issue
changes.
- **Center content window** → `DocumentSummaryView` renders **Revision Reason /
  Description / Justification / Detailed Background** (from the entry; "—" when
  absent) + back link + Download original. No timeline. Category panels/issue
  detail hide while it's open.
- **Right panel "For the talk"** → `DocumentProfileCard` (rightpanel.jsx) renders
  **number / title / date posted / submitter / requested resolution / related
  market sections**. Doc-level fields come from the entry; **requested resolution
  + related market sections** are fetched from the issue `Profile.json`
  (`timeline_requested_resolution`, `governing_document_sections`). In
  `RightPanel`'s card switch, `ctx.ruleDoc` takes precedence over the issue
  `RuleProfileCard`.

The report fields (`revision_reason`/`description`/`justification`/
`detailed_background`/`submitter`) are produced by `gen_mkt_doc_summaries.py --ai`
reading each document (see `Set-Paper-Trails-Document-Summary`); `onRuleDocClick`
is threaded app → `PaperTrailsIllustration` → each `<Cat>DetailView` →
`DocumentsSubmittedSection`.

**Download:** WAMP serves the original directly via `download_url`
(`…/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/<original document>`, %-encoded) — no rebuild.

COPMGRR issue IDs are zero-padded to 3 digits (`COPMGRR015`); all others are
plain integers.

**Schema compatibility:** profiles use the unified skill schema
(`issue_number`, `governing_document_sections`, `reason_for_revision` as
string *or* array). The right-panel cards read the unified keys with
legacy fallbacks (`nprr_number`, `protocol_sections_requiring_revision`,
`agreement_sections_requiring_revision`) and wrap reason values in
`asList()`. Keep that pattern when touching the cards.
`Summary.json` keys are per-category (`nprr_number` / `protocol_sections`,
`nogrr_number` / `guide_sections`, etc.) — match what the corresponding
`summarize_ercot_<cat>.py` script writes.

## Right Panel — Artifacts Behavior

Artifact items in the right panel's Artifacts tab are handled by
`onArtifactClick` in `app.jsx`:

- Items in `ARTIFACT_COMPONENTS` render a **native React panel** in the
  content window (component name looked up on `window` at render time).
  Currently: "ERCOT stakeholder process org chart" → `ErcotOrgChart`
  (defined in `meetingtracks.jsx`; themed by the app's CSS variables, no
  iframe, no height-fitting needed).
- Items in `ARTIFACT_SRCS` render their page in the content window as an
  injected iframe panel with self-refitting height. Currently:
  "ERCOT major milestones timeline" → `ERCOT Major Milestones.html`.
  Paths must carry the `/Power.Talks` prefix — the app is served under
  `localhost/Power.Talks/`, so a bare `/html/...` URL 404s.
- **Once-per-session rule (both kinds):** each panel is injected at most once
  per browser session. The first click renders it in the content window and
  scrolls it into view; ensuing clicks produce no additional output (the
  handler dedupes on `src`/`comp` in `injectedPanels`). A page reload starts
  a fresh session.
- All other artifact items just pre-fill the composer draft (`onRunPrompt`)
  and are repeatable by design.

## Routine Refresh — after downloader / profile / summary runs

1. Regenerate Profile.json and Summary.json first (see the
   `ERCOT-Market-Rules-Profile` and `ERCOT-Market-Rules-Summarization-and-Timeline`
   skills). Detail views and Quick runs pick these up with no UI change.
   Also (re)generate per-document summaries for any new `source_documents` via
   the `Set-Paper-Trails-Document-Summary` skill so the Document Summary view and
   download links resolve.
2. If issue lists changed (new issues, status moves Pending→Approved, new
   titles): run `python "html/regen_paper_trails_data.py"` to rewrite the
   `const <CAT>_<STATUS>` arrays in `html/src/data.jsx`.
3. Rebundle: `python "html/rebuild_standalone.py"` — must report all source
   files updated (11 entries as of June 2026).
4. Verify: hard-refresh (Ctrl+F5) on `http://localhost/...`, open the
   category homepage, click an issue, confirm the detail view and Quick runs
   panel load.

## Adding a New Category Homepage (e.g. OBDRR, RRGRR, VCMRR, SMOGRR)

1. **data.jsx** — add `const <CAT>_<STATUS>` arrays (only the statuses the
   category actually has) and register them in `window.DATA`.
2. **illustration.jsx** — add the category to `PAPER_TRAIL_CODES`; clone the
   closest existing homepage panel (NOGRR for 4-status categories, PGRR for
   3-status) and the `<Cat>DetailView` (adjust the fetch URL and JSON keys);
   wire them into the `active === "<CAT>"` branch.
3. **rightpanel.jsx** — clone a Quick runs card (ProfileCard or SummaryCard),
   adjust fetch URL, keys, and section label; add the case to the panel's
   context switch.
4. **app.jsx** — add `active<Cat>` state, reset effect, click handler, prop
   to `PaperTrailsIllustration`, and the key in the `RightPanel` context.
5. Rebundle and verify (steps 3–4 above).

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing `src/*.jsx` and expecting the page to change | The served page is a frozen bundle — always run `html/rebuild_standalone.py` afterwards |
| Opening via `file://` | All issue data 404s/fails — use `http://localhost` (WAMP must be running) |
| Forgetting COPMGRR zero-padding in fetch URLs | `COPMGRR{n:03d}` in both folder and file names |
| `.map` on `reason_for_revision` | It can be a string (new schema) or array (legacy) — use `asList()` |
| Adding list entries with `"` in titles | Breaks the JS string — replace with `'` |
| Assuming every category has a Pending list | SCR currently ships only Approved/Withdrawn/Rejected arrays; PGRR/RMGRR/NPRR/COPMGRR have no Rejected |
| Stale browser cache after rebundle | Hard-refresh (Ctrl+F5); the bundle is one big HTML file |
| Documents Submitted list empty though files exist | `source_documents` not populated — run `gen_mkt_doc_summaries.py` (the `Set-Paper-Trails-Document-Summary` skill) |
| Download button serves the JSON, not the file | Point `download_url` at the original document under the issue folder, not a summary JSON |
