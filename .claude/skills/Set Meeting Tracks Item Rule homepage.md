---
name: Set-Meeting-Tracks-Item-Rule-Homepage
description: Use when asked to set up or change the Meeting Tracks item (document) homepage in the Power.Talks web app — the detail view shown when a document is clicked on a Meeting Tracks group homepage, its metadata fields, the open-document link, or its Quick runs right panel.
trigger: When the user asks about the Meeting Tracks item/document homepage, clicking a meeting document, the document detail view, or opening a meeting file.
---

# Set Meeting Tracks Item (Document) Homepage

## Overview

On the Meeting Tracks **group homepage** (see
`Set-Meeting-Tracks-Groups-Homepage`), expanding a meeting lists its documents.
Clicking a document opens its **item homepage** in the content window — the
detail view for a single meeting document. For Meeting Tracks, the "item" is a
**document** (the analog of a Paper Trails issue's detail view).

The item homepage shows:
- A **back link** ("← `<group>` meetings") returning to the group homepage.
- An eyebrow `<COMMITTEE> · <date>` and the **filename** as the title.
- Fields: **Committee**, **Meeting date**, **Document type** (inferred from the
  extension — PDF, Word, Excel, PowerPoint, ZIP bundle, …).
- An **Open document** button linking to the actual file served from WAMP:
  `/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/<date>/<file>`
  (opens in a new tab).

Right panel ("Quick runs") is the same as the group homepage:
- **For the talk** → the parent meeting's profile (`MeetingProfileCard`, per
  `ERCOT Stakeholder Meeting Profile.md`), focused on this document's meeting
  date — graceful "not yet generated" fallback when absent.
- **Artifacts** → the full `ARTIFACTS` list (the Market Rules right-panel
  setting).

## File Map

| File | Role |
|---|---|
| `html/src/meetingtracks.jsx` | `MeetingTracksItemHome` (`window.MeetingTracksItemHome`): props `{ committee, date, file, groupName, onBack }`; renders the metadata fields + the WAMP open link; `docExt`/type map. |
| `html/src/app.jsx` | `activeMeetingDoc = { committee, date, file }` set by `onMeetingDocClick`; the render branch shows `MeetingTracksItemHome` when `activeMeetingDoc` is set, `onBack` clears it back to the group homepage. `activeMeetingDate` is set to the document's date (drives the profile). |
| `html/src/rightpanel.jsx` | `ctx.meetingDoc` makes `isMeetingGroup` true → For the talk (`MeetingProfileCard` for `meetingDoc.committee` + `meetingDate`) + full Artifacts. |

## Navigation model

```
Meeting Tracks tree  ──click group name──▶  Group homepage (meeting list)
                                              │
                                  ──click a document──▶  Item homepage (this skill)
                                              ◀── back link ──
```

State lives in `app.jsx`: `activeMeetingGroup` (committee) → `activeMeetingDoc`
({committee, date, file}). The content branch renders item ▸ group ▸ tree in
that precedence. Leaving the Meeting Tracks section resets all three.

## The document link

`MeetingTracksItemHome` builds the open URL from the committee folder, the ISO
date folder, and the filename, each `encodeURIComponent`-escaped:

```
/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/<committee>/<date>/<file>
```

This is the real downloaded file under `Documents Database/` served by WAMP — so
it only works over `http://localhost`, not `file://`. ZIP bundles download;
PDFs/Office files open or download per the browser.

## Extending the item view

The current item homepage is intentionally light (metadata + open link). To add
content (e.g. an AI document summary, extracted agenda section, or ballot
detail), generate a per-document or per-meeting JSON and fetch it here the same
way `MeetingProfileCard` fetches the meeting `Profile.json` — keep the graceful
"not yet generated" fallback. Don't block the open link on that fetch.

## Rebuild & Verify

1. `python "html/rebuild_standalone.py"`.
2. Hard-refresh, open Meeting Tracks → a group → expand a meeting → click a
   document.
3. Confirm: the item homepage shows committee/date/type, the back link returns
   to the group, **Open document** points at the correct WAMP path, and the
   right panel shows the meeting profile (or its fallback) plus full Artifacts.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Open link 404s | Path must be `/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/<committee>/<date>/<file>`, %-encoded; WAMP must be running |
| Editing `src/*.jsx` and expecting the page to change | Run `html/rebuild_standalone.py` |
| Item view shows the trimmed 3 artifacts | `ctx.meetingDoc` must be in context so `isMeetingGroup` is true → full list |
| Back link lands on the tree | `onBack` should clear only `activeMeetingDoc` (back to the group), not the group too |
| Profile card empty | `activeMeetingDate` must be set to the document's date when the item opens |
