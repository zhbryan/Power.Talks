---
name: Set-Paper-Trails-Category-Homepage
description: Use when asked to set up, refresh, or change a Paper Trails category homepage (NPRR, SCR, COPMGRR, NOGRR, PGRR, RMGRR) — the status list pages, the right-panel category introduction, the Artifacts list, or the refresh run log.
trigger: When the user asks about a category homepage in Paper Trails, the category introduction card, refreshing category lists, the run log, or the Artifacts shown in the right panel.
---

# Set Paper Trails Category Homepage

## Overview

A category homepage is what opens when a card in the Paper Trails 3×2 grid
is clicked: status list panels (Pending / Approved / Withdrawn / Rejected)
for that category in the center pane, plus category-level content in the
right panel. Selecting an individual issue switches the right panel to the
per-issue card (see the `Set-Paper-Trails-Item-Rule-Homepage` skill) and the
center pane to the issue detail view.

## Components

| Piece | Where |
|---|---|
| Category grid + list panels | `html/src/illustration.jsx` (`PAPER_TRAIL_CODES`, per-category homepage panels) |
| List data | `html/src/data.jsx` — `const <CAT>_<STATUS> = [{ n, title }, ...]`, registered in `window.DATA` |
| Right panel, "For the talk" tab | `CategoryIntroCard` in `html/src/rightpanel.jsx` (category selected, no issue) |
| Right panel, "Artifacts" tab | `ARTIFACTS` in `html/src/data.jsx` |
| List regeneration + run log | `html/regen_paper_trails_data.py` |
| Bundle rebuild | `html/rebuild_standalone.py` (required after ANY src or data edit) |

## Right Panel — Category Introduction ("For the talk" tab)

When a Paper Trails category homepage is open and **no issue is selected**,
the "For the talk" tab shows `CategoryIntroCard` (NOT the generic
"Suggested study runs", which remains for non-Paper-Trails sections).
Content lives in `CATEGORY_INTROS` in `html/src/data.jsx`, one entry per
category with exactly these blocks, in order:

| Block | Key | Notes |
|---|---|---|
| Code + review-body badge | `reviewBody` | Mono code (`np-num`) + pill badge, like the item card's status badge |
| Full name | `fullName` | Serif title (`np-title`), e.g. "Nodal Protocol Revision Request" |
| History | `history` | Origin and notable milestones of the rule type |
| Function & Purpose | `purpose` | What document it revises, what it covers, and its review path |
| Current Leadership | `leadership: [{ role, name }]` | One uppercase-label field per officer, like the item card's Sponsor/Email/Phone fields |
| Upcoming Meetings | `upcomingMeetings: [{ date: "YYYY-MM-DD", name }]` | Rendered as the NPRR-style dotted timeline (`np-tl`), nearest meeting's dot filled; filters to dates **after today** and shows the next 4 |

**Formatting contract:** the card uses the same visual vocabulary as the
per-issue `RuleProfileCard` via the shared `NP_CARD_CSS` constant in
`rightpanel.jsx` — mono section labels, dashed `np-divider` between blocks,
always-shown labels with `—` for missing values, and the dotted timeline.
Style changes to either card go into `NP_CARD_CSS` so both stay aligned
(see the `Set-Paper-Trails-Item-Rule-Homepage` skill).

Reviewing bodies (drive leadership + meetings): NPRR & SCR → **PRS**;
NOGRR & PGRR → **ROS**; RMGRR → **RMS**; COPMGRR → **WMS** (COPS was
absorbed into WMS — there is no COPS page on ercot.com anymore).

**Maintenance:** leadership and meeting dates are static data refreshed
manually from `https://www.ercot.com/committees/<prs|ros|rms|wms>` (last
refreshed 2026-06-11; date noted in the comment above `CATEGORY_INTROS`).
When all of a committee's `upcomingMeetings` dates have passed, the card
shows a "check ercot.com/committees" fallback — that is the signal to
refresh the arrays.

## Right Panel — Artifacts Tab

The Artifacts tab is **context-dependent** (logic in `rightpanel.jsx`):

- **Category homepage** (this skill — category selected, no issue) shows a
  **trimmed** set of 3: Make a podcast, Write a briefing note, Create a slide
  outline.
- **Item-rule homepage** (an issue selected — see
  `Set-Paper-Trails-Item-Rule-Homepage`) and every other non-ERCOT section show
  the **full** `ARTIFACTS` list (7 items).

The full list lives in `ARTIFACTS` in `data.jsx`. The category homepage hides a
fixed id set via `CATEGORY_HIDDEN_ARTIFACT_IDS = ["a2","a5","a7","a8"]` in
`rightpanel.jsx` (Draw a timeline, Draft a press release, Summarise as a tweet
thread, Generate a glossary — hidden 2026-06-16). To change what the category
homepage hides, edit that id list — do **not** delete entries from `ARTIFACTS`
(that would also strip them from the item-rule homepage).

**"Build a comparison table" was removed from `ARTIFACTS` entirely (2026-06-11)
— do not re-add it.** The ERCOT home section uses its own separate
`ERCOT_HOME_ARTIFACTS` list in `rightpanel.jsx`.

## Refresh Procedure (run after downloader / profile / summary updates)

```bash
python "html/regen_paper_trails_data.py"   # rewrites <CAT>_<STATUS> arrays + appends run log
python "html/rebuild_standalone.py"        # re-embeds src into the served bundle
```

### Run Log

Every `regen_paper_trails_data.py` run appends its main changes to
`html/paper_trails_run_log.txt`:

```
=== 2026-06-11 19:42:10 regen_paper_trails_data ===
  NPRR_PENDING: 37 -> 43
  NOGRR_PENDING: 6 -> 8
```

- Only arrays whose counts changed are listed (`no list changes` otherwise);
  skipped non-empty buckets with no array in `data.jsx` are logged as `SKIPPED`.
- The log is append-only history — consult it to see what past runs changed;
  do not truncate it casually.

## Verification

1. Hard-refresh `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html`
   (never `file://`).
2. Open each changed category: list panels show the new issues/statuses.
3. With no issue selected, the right panel "For the talk" tab shows the
   category introduction with all five blocks and only future meetings.
4. On a category homepage (no issue) the Artifacts tab shows 3 items (Make a
   podcast, Write a briefing note, Create a slide outline). Select an issue and
   the Artifacts tab shows the full 7-item list (timeline, press release, tweet
   thread, glossary restored) — never the comparison table.
5. `html/paper_trails_run_log.txt` has a new dated entry.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing src/data and expecting the page to change | The served page is a frozen bundle — run `rebuild_standalone.py` |
| Showing Suggested study runs on a category homepage | `RightPanel` must route `ctx.section === "paper-trails" && ctx.code` (and no issue) to `CategoryIntroCard` |
| Hard-coding "next meetings" as text | Keep `upcomingMeetings` as dated entries; the card filters `date > today` at render time |
| Pointing COPMGRR at COPS | COPS no longer exists — COPMGRRs are reviewed by WMS |
| Forgetting the run log | List regeneration goes through `regen_paper_trails_data.py`, which appends it automatically — don't hand-edit `data.jsx` arrays |
| Deleting timeline/press-release/tweet/glossary from `ARTIFACTS` to hide them on the category homepage | They must stay in `ARTIFACTS` (the item-rule homepage shows them) — hide them on the category homepage via `CATEGORY_HIDDEN_ARTIFACT_IDS` in `rightpanel.jsx` instead |
| Re-adding "Build a comparison table" | Removed from `ARTIFACTS` entirely by design |
