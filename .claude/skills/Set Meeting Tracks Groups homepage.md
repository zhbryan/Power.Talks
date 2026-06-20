---
name: Set-Meeting-Tracks-Groups-Homepage
description: Use when asked to set up, change, or debug the Meeting Tracks group homepage in the Power.Talks web app — the per-group meeting list shown when a group name is clicked in the Meeting Tracks tree (year-grouped meetings, document lists, the meeting manifest, or the group's Quick runs right panel).
trigger: When the user asks about the Meeting Tracks group/committee homepage, the meeting list view, the meetings manifest, clicking a group in the tree, or the group's Quick runs panel.
---

# Set Meeting Tracks Group Homepage

## Overview

A **group homepage** opens when a group name is clicked in the Meeting Tracks
tree (see `Set-Meeting-Tracks-Homepage`). The content window switches from the
tree to that committee's **meeting list**, grouped by year:

- **Year sections** — newest first; the **current year is expanded**, past years
  **collapsed**. Each year header shows its meeting and document counts.
- **Meeting rows** (inside a year) — date + document count; clicking a row
  expands its **document list** (collapsed by default) and focuses that meeting
  (drives the right-panel profile).
- **Documents** — each is clickable and opens its **Item homepage**
  (see `Set-Meeting-Tracks-Item-Rule-Homepage`).
- A **back link** ("← ERCOT Stakeholder Process") returns to the tree.

Right panel ("Quick runs") on a group/item homepage:
- **For the talk** → the meeting profile (`MeetingProfileCard`), per
  `ERCOT Stakeholder Meeting Profile.md` — fetched live, with a graceful
  "not yet generated" fallback when the profile is missing.
- **Artifacts** → the **full** `ARTIFACTS` list (the Market Rules right-panel
  setting — same as the Paper Trails item-rule homepage), not the trimmed
  3-item set used on the tree landing.

## File Map

| File | Role |
|---|---|
| `html/src/meetingtracks.jsx` | `MeetingTracksGroupHome` (`window.MeetingTracksGroupHome`): fetches the manifest, renders the year/meeting/document tree. Also `GROUP_ALIAS` + `resolveCommittee` map tree nodes → committee folders. |
| `html/src/app.jsx` | Meeting Tracks navigation state: `activeMeetingGroup` / `activeMeetingGroupName` / `activeMeetingDate` / `activeMeetingDoc`; handlers `onMeetingGroupClick`, `onMeetingDocClick`; the render branch and `context` passed to `RightPanel`. |
| `html/src/rightpanel.jsx` | `isMeetingGroup` / `onMeetingTree` drive the panel; `MeetingProfileCard` (For the talk) and the full-vs-trimmed `activeArtifacts`. |
| `Database Codes/download_STKHDR_Meets/gen_stkhdr_manifest.py` | **Generates the manifests** the homepage reads. Run after a download pass. |

## Data — the meeting manifest

The browser cannot list folders, so each committee folder has a generated
manifest the homepage fetches at runtime:

```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/_manifest.json
```

Shape:

```json
{ "committee": "TAC", "generated": "…", "meeting_count": 214,
  "meetings": [ { "date": "2026-05-19", "doc_count": 12, "docs": ["…", "…"] }, … ] }
```

Meetings are newest-first; `docs` excludes `.tmp` files and the manifest itself.
Fetched at `/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/_manifest.json`.

**Regenerate after every download run:**

```bash
python "Database Codes/download_STKHDR_Meets/gen_stkhdr_manifest.py"
```

Manifests live under `Documents Database/` (gitignored) — they're generated
artifacts, not committed.

## Tree node → committee mapping

`MeetingTracksGroupHome` is keyed by the **document-database committee folder**
(e.g. `TAC`, `ROS`, `SPWG`). The org tree's node ids predate the downloader's
abbreviations, so `resolveCommittee(node)` in `meetingtracks.jsx` maps them:

- `GROUP_ALIAS` fixes mismatches: `BOD→BOARD`, `PLWG→PRS`, `SAWG→SPWG`
  (tree's System Protection node), `SAWG2→SAWG`, `TDTWG→TDTMS`.
- Sunset leaf nodes use their tag (`TXSET`, `MSWG`, …).
- The Sunsetted root and per-parent grouping nodes resolve to `null` (not
  navigable — they only expand/collapse).

A group with no downloaded data shows a clean "No downloaded meetings on file
for `<COMMITTEE>` yet." (the manifest 404s). To extend coverage, add the
committee to the downloader registry, download, regenerate manifests, and (if
needed) add an alias.

## Right panel wiring (`rightpanel.jsx`)

- `isMeetingGroup = isMeetingTracks && (ctx.meetingGroup || ctx.meetingDoc)`.
- `onMeetingTree = isMeetingTracks && !isMeetingGroup` (the tree landing).
- Tabs: "For the talk" is hidden on `onMeetingTree`, shown on `isMeetingGroup`.
  An effect forces Artifacts on the tree landing and "For the talk" (runs) when
  a group/item opens.
- `activeArtifacts`: trimmed (3) on `onMeetingTree`; **full** `ARTIFACTS` on
  `isMeetingGroup`.
- For the talk renders `<MeetingProfileCard committee=… date={ctx.meetingDate}/>`.
  `meetingDate` is set when a meeting row is expanded or a document is opened;
  with no date it shows "Select a meeting or document to see its profile."

## Rebuild & Verify

1. `python "…/gen_stkhdr_manifest.py"` (if downloads changed), then
   `python "html/rebuild_standalone.py"`.
2. Hard-refresh, open Meeting Tracks, click a group name (e.g. *Technical
   Advisory Committee*).
3. Confirm: year sections (current expanded, past collapsed) with meeting/doc
   counts; expanding a meeting lists its documents; the right panel shows
   "For the talk" + "Artifacts" (full 7); a document opens its Item homepage.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Group shows "no meetings" though files exist | Manifest stale or committee not aliased — run `gen_stkhdr_manifest.py`, check `GROUP_ALIAS`/`resolveCommittee` |
| Editing `src/*.jsx` and expecting the page to change | Run `html/rebuild_standalone.py` |
| Opening via `file://` | Manifest/profile fetches fail — use `http://localhost` |
| Showing the trimmed 3 artifacts on a group homepage | The trim applies only to `onMeetingTree`; group/item uses the full list |
| Expecting all years expanded | Only the current year is expanded by default; past years collapse |
