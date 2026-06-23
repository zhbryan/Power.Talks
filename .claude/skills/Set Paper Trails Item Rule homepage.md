---
name: Set-Paper-Trails-Item-Rule-Homepage
description: Use when asked to set up, change, or fix the per-issue "Quick runs" card in the Power.Talks right panel — the profile card shown when a specific market rules issue (NPRR, SCR, COPMGRR, NOGRR, PGRR, RMGRR) is selected in Paper Trails. Defines the standard field set, order, and timeline format every category must follow.
trigger: When the user asks about the Quick runs panel for a rule item, the fields shown for a selected NPRR/SCR/COPMGRR/NOGRR/PGRR/RMGRR, or wants the per-issue right-panel card changed or extended to a new category.
---

# Set Paper Trails Item Rule Homepage (Quick runs card)

## Overview

When an issue is selected on a Paper Trails category homepage, the right
panel ("Quick runs" → "For the talk" tab) shows a profile card for that
issue. One shared component renders the card for **all six categories**:

- Component: `RuleProfileCard({ cat, num })` in `html/src/rightpanel.jsx`
- Config: `RULE_CARD_CFG` (same file) — per-category section label and
  COPMGRR's 3-digit zero padding
- Data: the issue's `Profile.json`, fetched live:

```
/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/Quick%20runs/<ISSUE_ID>%20Profile.json
```

Do **not** add per-category card components — extend `RuleProfileCard` /
`RULE_CARD_CFG` instead. The card is selected in `RightPanel`'s context
switch (`hasNprr ? <RuleProfileCard cat="NPRR" num={ctx.nprr} /> : ...`).

## Standard Field Set — required for every category, in this order

| # | Block | Profile.json source | Notes |
|---|---|---|---|
| 1 | Issue ID + status badge | `status` | Badge colors: Approved=ok, Withdrawn=muted, Pending/Rejected=warn |
| 2 | Title | `title` | **Always shown** — falls back to the issue ID if null |
| 3 | Sponsor | `sponsor_name` (+ ` · sponsor_company` when present) | |
| 4 | Email | `sponsor_email` | |
| 5 | Phone | `sponsor_phone` | |
| 6 | Market Segment | `market_segment` | |
| 7 | Requested Resolution | `timeline_requested_resolution` | |
| 8 | Date Posted | `date_posted_decision` | |
| 9 | Reason for Revision | `reason_for_revision` | String **or** array — always wrap in `asList()` |
| 10 | Timeline | `timeline` (`[{date, event, doc}]`) | NPRR-style dotted vertical timeline (see below) |

> **Documents Submitted is NOT on this Quick-runs card.** The submitted-document
> list lives in the **center content window** (the issue detail view), as a
> "Documents Submitted" section **below Current Status** — see
> `Set-Paper-Trails-Homepage`. Do not re-add it to `RuleProfileCard`.
>
> **When a document is opened, this card is replaced by `DocumentProfileCard`**
> (the per-document metadata: number, title, date posted, Sponsor, requested
> resolution, related market sections). `RuleProfileCard` shows only when an
> issue is selected but no document is open (`ctx.ruleDoc` takes precedence).

> **Governing-document sections are intentionally NOT on this card** (removed
> 2026-06-12 by request) — do not re-add a "Protocol Sections" block. The
> sections remain available in `Profile.json` and on the center detail view.

**Empty-value rule:** every label above is always rendered. A field whose
value was not extracted shows an em dash (`—`) — never hide the row. The
`Field` helper inside `RuleProfileCard` implements this; reasons and
timeline render a literal `—` line when empty.

## `RULE_CARD_CFG`

Per-category config now only carries COPMGRR's zero padding:
`COPMGRR: { pad: 3 }` (URLs/IDs use `COPMGRR015`).

## Timeline Format (the NPRR format — mandatory for all categories)

Vertical dotted rail (`np-tl` CSS classes), one row per event, chronological
(profile timelines are stored sorted ascending by date):

```jsx
<div className="np-tl">
  {timeline.map((t, i) => (
    <div key={i} className="np-tl-row">
      <div className={`np-tl-dot ${i === timeline.length - 1 ? "last" : ""}`} />
      <span className="np-tl-date">{t.date || "—"}</span>
      <span className="np-tl-ev"><b>{t.event}</b></span>
    </div>
  ))}
</div>
```

The last dot is filled (`np-tl-dot last`) to mark the most recent event.
Do not use the old "Recent Activity" table format (removed June 2026) and
do not truncate to the last N events — show the full timeline.

## Data Contract

The card depends on the unified profile schema written by the
`ERCOT-Market-Rules-Profile` skill (`issue_number`,
`governing_document_sections`, `timeline`, `source_documents`, ...). If a
card shows mostly em dashes, the profile is sparse — refresh it with that
skill's Update Mode, not by changing the UI. A 404 renders a hint to run
the Profile skill.

## Change Procedure

1. Edit `RuleProfileCard` / `RULE_CARD_CFG` in `html/src/rightpanel.jsx`.
   Visual styles live in the shared `NP_CARD_CSS` constant (same file), which
   also formats the category-level `CategoryIntroCard` — style changes there
   affect both cards by design.
2. Adding a category: add its `RULE_CARD_CFG` entry, the `has<Cat>` flag +
   switch arm in `RightPanel`, and the context key in `app.jsx` (see the
   `Set-Paper-Trails-Homepage` skill for the full new-category checklist).
3. Syntax check: `npx -y esbuild html/src/rightpanel.jsx --loader:.jsx=jsx --outfile=NUL`
4. Rebundle: `python "html/rebuild_standalone.py"` (the served page is a
   frozen bundle — source edits are invisible until this runs).
5. Verify on `http://localhost` (never `file://`) with a hard refresh:
   select one issue in each category; confirm all 10 blocks render and
   missing values show `—`.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Hiding empty fields | All labels always render; missing values show `—` |
| Calling `.map` on `reason_for_revision` directly | It may be a string — use `asList()` |
| Fetching `Summary.json` for the Quick runs card | The card reads `Profile.json` for every category (Summary.json feeds the center detail view) |
| Re-adding the document list to this card | The "Documents Submitted" list lives in the center detail view (below Current Status), not the Quick-runs card — see `Set-Paper-Trails-Homepage` |
| Forgetting COPMGRR zero-padding | `RULE_CARD_CFG.COPMGRR.pad = 3` drives both the URL and the displayed ID |
| Editing src without rebundling | Run `html/rebuild_standalone.py` after every change |
