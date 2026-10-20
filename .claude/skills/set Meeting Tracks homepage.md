---
name: Set-Meeting-Tracks-Homepage
description: Use when asked to set up, update, or change the Meeting Tracks section of the Power.Talks web app — the ERCOT Stakeholder Process explorer tree shown in the content window, the committee hierarchy data, or the Meeting Tracks right-panel (Quick runs) behavior, including the "Meeting Timeline" tab.
trigger: When the user asks to change the Meeting Tracks content, the ERCOT stakeholder process tree/org chart, the committee hierarchy, the Meeting Tracks Quick runs / Artifacts panel, or the Meeting Timeline tab showing upcoming/recent stakeholder meetings.
---

# Set Meeting Tracks Homepage

## Overview

Meeting Tracks is the `meeting-tracks` section. Its content window shows the
**ERCOT Stakeholder Process as a Windows-Explorer-style folder tree** —
expandable folders (committees/subcommittees with chevrons + folder icons) and
leaf files (working groups). The active committee hierarchy is **fully expanded
by default** so the whole structure is visible without an inner scroll; a
collapsible **"Sunsetted / Inactive Groups"** branch sits at the bottom.

There is **no per-node summary**. Clicking a **group name** opens that group's
homepage (the meeting list — see `Set-Meeting-Tracks-Groups-Homepage`); the
**chevron** expands/collapses children. On the tree landing (no group open) the
right panel ("Quick runs") has **no "For the talk" tab**; it has two tabs —
**Meeting Timeline** (added 2026-10-20, the default here) and **Artifacts**,
trimmed to three: *Make a podcast, Write a briefing note, Create
a slide outline*. Once a group or document is open, the right panel switches to
**For the talk** (meeting profile) + the full **Artifacts** list — that wiring
lives in `Set-Meeting-Tracks-Groups-Homepage` / `Set-Meeting-Tracks-Item-Rule-Homepage`.

Open via **http://localhost/Power.Talks/html/Power.Talks%20home%20page.html**.

## File Map

| File | Role |
|---|---|
| `html/src/meetingtracks.jsx` | **`MeetingTracksOrgChart`** (`window.MeetingTracksOrgChart`): the explorer tree. Hierarchy data in `ERCOT_ORG` (nested) and `SUNSET_GROUPS` (flat, grouped by `parent`). Also defines `ErcotOrgChart` (a different component, used as an ERCOT-home artifact). |
| `html/src/app.jsx` | Renders `<MeetingTracksOrgChart selected={activeMeetingNode} onSelect={onMeetingNodeClick}/>` for `activeSection === "meeting-tracks"`; passes `context={{ section, node, ... }}` to `RightPanel`. |
| `html/src/rightpanel.jsx` | `isMeetingTracks = ctx.section === "meeting-tracks"` drives the panel: hides "For the talk", forces the Artifacts tab, and trims Artifacts via `CATEGORY_HIDDEN_ARTIFACT_IDS`. Also holds **`MeetingTimelinesCard`** + the `mtlDate`/`mtlShort` helpers and the `TIMELINE_FEED` path. |
| `Database Codes/download_STKHDR_Meets/gen_stkhdr_timeline.py` | **Generates the Meeting Timeline feed** (`_timeline.json`) the tab reads. Step 7b of `run_routine.py`. |
| `html/rebuild_standalone.py` | Re-embeds `src/*.jsx` into the served bundle. Run after any edit. |

## The content window (`MeetingTracksOrgChart`)

- **Data:** `ERCOT_ORG` is the nested active hierarchy (`{ id, name, tag, children }`).
  `SUNSET_GROUPS` is a flat list of `{ tag, parent, name }` inactive bodies;
  the component groups them by `parent` (using `SUNSET_PARENTS`) into the
  collapsible "Sunsetted / Inactive Groups" folder. The tree renders an array
  of roots: `[ERCOT_ORG, sunsetFolder]`.
- **Expansion:** initial `expanded` state walks `ERCOT_ORG` and sets every node
  with children to `true` (active tree fully open); the sunset branch stays
  collapsed. `toggle(id)` flips a node.
- **Rendering:** `renderNode(node, depth)` draws a row — chevron (for folders),
  a folder/file icon (`FolderIcon`/`FileIcon`), the `tag` badge, the `name`,
  and a child-count pill. Clicking the **row/name** calls
  `onGroupClick(committee, name)` where `committee = resolveCommittee(node)`
  (navigates to the group homepage); the **chevron** toggles expand/collapse.
  Non-committee folders (the Sunsetted root and its per-parent nodes) resolve to
  `null` and only toggle. **Do not re-introduce a detail/summary panel** — the
  old `NodeInfoPanel` / `mt-detail` column and the per-node meeting records were
  removed by request.
- **Height:** the card (`.pt-orgchart`) is `display: block` (single column, no
  inner `max-height`) so the fully-expanded tree shows at natural height; the
  page scroll (`.pt-main-scroll`) handles overflow.

### Editing the hierarchy

- **Add/rename an active group:** edit `ERCOT_ORG` (nested) — add a `{ id, name,
  tag }` (leaf) or a node with its own `children`. `id` must be unique; `tag` is
  the short badge.
- **Add an inactive group:** append `{ tag, parent, name }` to `SUNSET_GROUPS`
  with `parent` one of `SUNSET_PARENTS` (`TAC`, `ROS`, `WMS`, `RMS`, `PRS`,
  `COPS`, `Board`, `Finance`, `Other`, `Nodal`).

> The unused helpers `NodeInfoPanel`, `MeetingListPanel`, `SunsetGroupsPanel`,
> and the `MEETING_RECORDS`/`NODE_INFO` data remain defined in the file but are
> no longer rendered. Leave or remove them; do not wire them back into the tree.

## The right panel (Quick runs) on Meeting Tracks

> This section describes the **tree landing** (no group open). When a group or
> document is open (`ctx.meetingGroup`/`ctx.meetingDoc`), the panel instead
> shows **For the talk** (meeting profile) + the full Artifacts list — see
> `Set-Meeting-Tracks-Groups-Homepage`. The gate is `onMeetingTree =
> isMeetingTracks && !isMeetingGroup`.

On the tree landing, `onMeetingTree` drops the "For the talk" tab, adds its own
"Meeting Timeline" tab, and is treated like `isCategoryHome` for the trimmed
artifact set:

- **No "For the talk" tab** — the tab button is gated `{!isErcotHome && !onMeetingTree && !isStatsHome && (…)}`,
  and the runs content is gated the same way.
- **"Meeting Timeline" tab** — a `{onMeetingTree && (…)}` tab button sets
  `tab === "timeline"`, whose content is `{tab === "timeline" && onMeetingTree &&
  <MeetingTimelinesCard />}`. It is the **default tab on the tree landing**
  (`if (onMeetingTree) setTab("timeline"); else if (isErcotHome || isStatsHome)
  setTab("artifacts")`), and a guard effect bounces `tab === "timeline"` back to
  Artifacts the moment `onMeetingTree` goes false — otherwise opening a group
  would strand the panel on a tab that renders nothing.
- **Forced Artifacts tab** elsewhere — ERCOT home and Stats Illustrator.
- **Trimmed Artifacts (3 items)** — `activeArtifacts` filters the full `ARTIFACTS`
  list by `CATEGORY_HIDDEN_ARTIFACT_IDS` (`["a2","a5","a7","a8"]`), leaving
  *Make a podcast (a1)*, *Write a briefing note (a3)*, *Create a slide outline (a6)*.
  This is the same trim used by the Paper Trails category homepage, so changing
  that id list affects both — see `Set-Paper-Trails-Category-Homepage`.
## The "Meeting Timeline" tab (`MeetingTimelinesCard`)

A vertical timeline of **every ERCOT stakeholder meeting in a rolling ±1 month
window**, on its own tab on the Meeting Tracks tree landing. It is deliberately
**kept out of the Artifacts tab** — do not merge the two back together.

- **Layout** — a 2px centre line (`.mtl::before`, left 50%), one `.mtl-row` per
  meeting, **alternating sides by index**: even rows get `is-l` (cell is the
  left half, right-aligned), odd rows `is-r` (`margin-left:50%`, left-aligned).
  A dot (`.mtl-dot`) sits on the centre line at each row.
- **Order** — top to bottom is **past → future**; the feed is already sorted
  oldest-first, so the component must not re-sort. Past rows carry `is-past`
  (muted dot/date/name); a dashed **"Today · <date>"** marker is injected before
  the first non-past row (`todayAt = meetings.findIndex(m => !m.past)`), and
  that row gets `is-next` (filled, haloed dot). If every meeting is past,
  `todayAt === -1` and the marker is appended at the bottom instead.
- **Each entry** shows the date (`mtlDate` → `"Wed, Oct 28"`, parsed at local
  noon so the weekday can't slip a day) and the meeting name as an
  `<a target="_blank" rel="noopener noreferrer">` to **that meeting's homepage on
  ercot.com** (the `/calendar/<MMDDYYYY>-<SLUG>` page — the same destination the
  `ERCOT-Stakeholder-Meetings-Links` skill treats as a meeting's canonical link).
  The committee's full name is the link's `title`. When documents are already
  downloaded, a `N docs on file` line is added.
- **Header** — the window range (`mtlShort(feed.from) – mtlShort(feed.to)`) plus
  the meeting count. The tab button already carries the title, so the card does
  **not** repeat it.

### Data — the timeline feed

```
Documents Database/ERCOT.STKHDR.MEETS/_timeline.json
{ generated, window_days, from, to, today, meeting_count,
  meetings: [ { committee, committee_full_name, date, name, url,
                past, on_file, doc_count } ] }      # oldest first
```

Written by `Database Codes/download_STKHDR_Meets/gen_stkhdr_timeline.py`, which
re-scrapes each committee landing page on ercot.com — **the per-committee
`_manifest.json` files cannot be used**, because they only list meetings whose
documents were already downloaded and therefore contain no future meetings.
The generator is **step 7b of the daily routine** (`run_routine.py`, right after
the group manifests), so the window rolls forward on its own each night:

```bash
python "Database Codes/download_STKHDR_Meets/gen_stkhdr_timeline.py"   # --window N, --quiet
```

The feed lives under `Documents Database/` (gitignored) — a generated artifact,
not committed. See `ERCOT-Stakeholder-Meeting-Downloader` for the generator's
scraping rules (cancelled / rescheduled handling, name derivation).

## Rebuild & Verify

1. `python "html/rebuild_standalone.py"` — must report all source files updated.
2. Hard-refresh (Ctrl+F5) and open Meeting Tracks (sidebar or the ERCOT-home
   Quick Access tile).
3. Confirm: the content window shows the full expanded ERCOT Stakeholder Process
   folder tree with folder icons and **no summary panel**; the right panel opens
   on a **Meeting Timeline** tab (alternating left/right, Today marker in the
   middle, meeting names opening ercot.com in a new tab) with a second
   **Artifacts** tab holding exactly the three items above — and switching to a
   group homepage leaves the Timeline tab behind for *For the talk*.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing `src/*.jsx` and expecting the page to change | The served page is a frozen bundle — run `rebuild_standalone.py` |
| Re-adding the node summary / meeting records | Removed by request — the tree is browse-only (expand/collapse) |
| Constraining the tree with an inner `max-height` | The structure must show full height — keep `.pt-orgchart` `display: block`, no inner scroll |
| Showing "For the talk" on Meeting Tracks | Keep the `!isMeetingTracks` gate on the tab button and the runs content |
| Deleting artifacts from `ARTIFACTS` to trim them here | Hide via `CATEGORY_HIDDEN_ARTIFACT_IDS`; deleting also strips them from the item-rule homepage |
| Building the Meeting Timeline from the per-committee `_manifest.json` | Manifests only hold meetings with downloaded documents — no future meetings. Use `_timeline.json` from `gen_stkhdr_timeline.py` |
| Timeline empty or stale | Feed missing/old — run `gen_stkhdr_timeline.py` (routine step 7b); over `file://` the fetch fails, use `http://localhost` |
| Re-sorting the timeline in the component | The feed is already oldest-first; sorting again breaks the past→future order and the Today marker |
| Putting the timeline in the Artifacts tab, or dropping the `tab === "timeline"` guard effect | It owns a separate tab gated on `onMeetingTree`; without the guard, opening a group strands the panel on an empty tab |
