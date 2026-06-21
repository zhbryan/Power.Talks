---
name: ERCOT-Stakeholder-Meeting-Profile
description: Use when asked to create, build, or generate a profile or summary JSON for a specific ERCOT stakeholder committee meeting (ROS, TAC, PRS, WMS, RMS, Board, or any active subgroup).
---

# ERCOT Stakeholder Meeting Profile Creator

## Overview

Creates a structured JSON profile file for a specific ERCOT stakeholder committee meeting, extracting key metadata from the meeting documents already downloaded to the local folder. The output file is saved in a `Quick runs` sub-folder under the meeting date folder.

## Scope — Active Committees

This skill applies to all in-scope committees listed in `ERCOT Stakeholder Meetings Links.md`. Use the exact abbreviations from that file:

`Board` · `FA` · `HRG` · `TS` · `TAC` · `LLWG` · `CFSG` · `RTCBTF` · `PRS` · `RMS` · `TDTMS` · `RMTTF` · `ROS` · `IBRWG` · `BSWG` · `DWG` · `MWG` · `NDSWG` · `OWG` · `OTWG` · `PDCWG` · `PLWG` · `SPWG` · `SSWG` · `VPWG` · `WMS` · `CMWG` · `DSWG` · `SAWG` · `WMWG` · `IBRTF`

## Input

- **Committee abbreviation** — e.g. `ROS`
- **Meeting date** — ISO 8601, e.g. `2025-01-09`

## Output Location

```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/YYYY-MM-DD/Quick runs/<COMMITTEE>-YYYY-MM-DD Profile.json
```

- Create `Quick runs/` if it does not already exist.
- File name format: `<COMMITTEE>-YYYY-MM-DD Profile.json` — e.g. `ROS-2025-01-09 Profile.json`.

## Source Folder

```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/YYYY-MM-DD/
```

Documents are downloaded by `Database Codes/download_ercot_ros.py` (ROS) or the equivalent committee downloader.

---

## Document Type Reference

Identify each file's role by keywords in the filename. Read all documents present; extract what is available.

| Filename keyword(s) | Document type | Extract |
|---------------------|---------------|---------|
| `agenda` | Agenda | Meeting date, chair opening, agenda item titles and numbers |
| `APPROVED-Minutes` / `minutes` / `Minutes` | Minutes (approved or draft) | Key discussion topics, action items, attendance note |
| `combined-ballot` / `ballot` / `Ballot` | Combined ballot (`.xls`) | Ballot items (NPRR/NOGRR/etc. numbers), vote counts, results |
| `segment_representative` / `segment-rep` | Segment representatives | Chair name, Vice Chair name |
| `_report_to_` / `Report-to-` / `report-to-ros` | Working group report (`.pptx`/`.docx`) | Reporting WG abbreviation |
| `meeting-materials` / `Meeting-Materials` | Materials bundle (`.zip`) | **Excluded** — `.zip` archives never appear in `documents` |
| `Revision-Request` / `revision-request` | Revision request bundle (`.zip`) | **Excluded** — `.zip` archives never appear in `documents` |

> **No ZIP links in the content window.** Any `.zip` file (case-insensitive) is
> excluded from the `documents` array — matching the meeting manifest and the
> group homepage, which never surface a zip link. Read inside a zip only if you
> need its contents for another field; never list the zip itself.

---

## Reading Strategy

| Extension | Method |
|-----------|--------|
| `.docx` | `python-docx`: `Document(path)` — read `.paragraphs` and `.tables` |
| `.doc`  | `win32com.client`: open with `Word.Application`, read `.Content.Text` |
| `.xls`  | Binary string extraction — search for ballot item text and vote counts |
| `.xlsx` | `openpyxl`: `load_workbook(path, read_only=True, data_only=True)` |
| `.pptx` | `python-pptx`: iterate slides, read `.shapes` text frames |

**For `.doc` via win32com:**
```python
import win32com.client, os
word = win32com.client.Dispatch("Word.Application")
word.Visible = False
doc = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
text = doc.Content.Text
doc.Close(False)
word.Quit()
```

**For `.xls` ballot vote extraction:**
```python
import re
with open(path, "rb") as f:
    data = f.read()
strings = [s.decode("ascii", errors="ignore") for s in re.findall(rb"[\x20-\x7e]{10,}", data)]
ballot_lines = [s for s in strings if any(k in s.upper() for k in ("NPRR", "NOGRR", "PGRR", "FOR", "AGAINST", "MOTION"))]
```

---

## Two-tier summary model (what the right panel shows)

The same profile feeds **two different "Quick runs / For the talk" views**, and
their summary content must be **different**:

| Level | Opened when… | Summary content | JSON source |
|-------|--------------|-----------------|-------------|
| **Group homepage** | a group name is clicked (no specific meeting) | Introduction to the **group** — leadership, voting parties, voting structure, mandate | `group_summary` (and `committee_full_name` / `chair` / `vice_chair`) |
| **Meeting homepage** | a specific meeting date/document is opened | Summary of **that meeting** — topics, debates/discussion, voting outcomes | `meeting_summary` (and `documents`) |

`group_summary` is **group-level** (identical across all the group's meetings).
`meeting_summary` is **meeting-level** (unique per meeting). Do not repeat the
group introduction inside the meeting view — keep the two cleanly separated.

## Profile Fields

Extract the following fields. Use `null` for any field not found; use `[]` for empty arrays.

| # | JSON Key | Source |
|---|----------|--------|
| 1 | `committee` | Committee abbreviation (from user input) |
| 2 | `committee_full_name` | Full name from `ERCOT Stakeholder Meetings Links.md` |
| 3 | `meeting_date` | ISO 8601 date (YYYY-MM-DD) |
| 4 | `meeting_type` | `Regular` / `WebEx` / `Email Vote` / `Special` / `Joint` / `Info Session` — infer from calendar URL slug or agenda text |
| 5 | `calendar_url` | `https://www.ercot.com/calendar/MMDDYYYY-<SLUG>` |
| 6 | `chair` | From segment reps doc or agenda opening |
| 7 | `vice_chair` | From segment reps doc or agenda opening |
| 7a | `group_summary` | **Group-level.** Object summarizing the meeting **group** — leadership, voting parties, structure, mandate (see below). Shown on the group homepage. Independent of the individual meeting. |
| 7b | `meeting_summary` | **Meeting-level.** Object summarizing **this meeting** — `topics`, `debates`, `voting_outcomes` (see below). Shown on the meeting homepage. |
| 8 | `agenda_items` | Array of agenda item title strings, in order |
| 9 | `ballot_results` | Array of `{item, motion, for, against, abstain, result}` objects from ballot `.xls` |
| 10 | `working_group_reports` | Array of WG abbreviations that submitted a report (e.g. `["NDSWG", "PLWG", "DWG"]`) |
| 11 | `key_discussion_topics` | Array of plain-text topic summaries from minutes |
| 12 | `action_items` | Array of action items from minutes |
| 13 | `documents` | Array of filenames in the meeting folder, **excluding `.zip` archives** (case-insensitive), `.tmp` files, and the manifest |
| 14 | `next_meeting_date` | ISO 8601 if mentioned in minutes or agenda; otherwise `null` |

## JSON Template

```json
{
  "committee": null,
  "committee_full_name": null,
  "meeting_date": null,
  "meeting_type": null,
  "calendar_url": null,
  "chair": null,
  "vice_chair": null,
  "group_summary": {
    "overview": null,
    "leadership": null,
    "voting_parties": [],
    "voting_structure": null
  },
  "meeting_summary": {
    "topics": [],
    "debates": [],
    "voting_outcomes": []
  },
  "agenda_items": [],
  "ballot_results": [],
  "working_group_reports": [],
  "key_discussion_topics": [],
  "action_items": [],
  "documents": [],
  "next_meeting_date": null
}
```

## ballot_results item template

```json
{
  "item": "NPRR1234",
  "motion": "Motion text as stated in ballot",
  "for": 0,
  "against": 0,
  "abstain": 0,
  "result": "Approved"
}
```

## group_summary — the meeting group profile

`group_summary` describes the **committee/group itself**, not the single meeting.
It is the same across every meeting of a group, so it can be reused; refresh it
from the live group page only when leadership changes.

| Key | Content | Source |
|-----|---------|--------|
| `overview` | 1–2 sentences on the group's mandate and where it sits in the stakeholder hierarchy | `ERCOT Introduction.md` / `ERCOT Stakeholder Org Chart.md`; group's `ercot.com/committees/<path>` page |
| `leadership` | Plain-text summary of current leadership, e.g. `Chair: Sandeep Borkar; Vice Chair: Shane Thomas` plus any notes (newly promoted, co-chairs, vacancy) | "Latest … Chair/VC" table in `ERCOT Stakeholder Meetings Links.md` §1; segment-rep doc if present |
| `voting_parties` | Array of the voting blocs/members that hold a vote in this group | Segment-rep doc; ERCOT market-segment model (see below) |
| `voting_structure` | How votes are cast and tallied (segment-weighted voting, simple/​two-thirds majority, advisory-only) | Group charter / `ERCOT Introduction.md` |

**ERCOT market-segment voting model.** TAC and its subordinate subcommittees
(PRS, ROS, RMS, WMS) and most working groups vote by **market segment**, not by
headcount. The standard voting segments are:

```
Consumer · Cooperative · Independent Generator · Independent Power Marketer ·
Independent Retail Electric Provider · Investor Owned Utility · Municipal
```

When a segment-representative document is present, list the actual member
companies/representatives per segment in `voting_parties`. Otherwise populate
`voting_parties` with the standard segments above and note in `voting_structure`
that the group uses ERCOT market-segment voting. Working groups that are advisory
(report up rather than ballot) should say so in `voting_structure` and may leave
`voting_parties` as `[]`.

### Board voting parties — update scheme

The Board and its committees (`BOARD`, `FA`, `HRG`, `TS`) are **not**
market-segment bodies, so their `voting_parties` are the **named directors**, not
segments. Maintain them from the live ERCOT pages:

| Source | Use for |
|--------|---------|
| `https://www.ercot.com/about/governance/directors` | The 8 independent directors (the voting members) + Chair/Vice Chair |
| `https://www.ercot.com/committees/board/finance_audit` | F&A committee roster |
| `https://www.ercot.com/committees/board/hr_governance` | HR&G committee roster |
| `https://www.ercot.com/committees/board/tech-security` | T&S committee roster |

**When to refresh:** ERCOT posts a news release whenever directors are appointed
(e.g. `ercot.com/news/release/...`). Re-verify on each major update and at least
annually. **The eight independent directors are the voting members**; the ex
officio members — President & CEO and PUCT Chair (non-voting), plus the PUCT
Commissioner and OPUC Public Counsel — are noted in `voting_structure`, not in
`voting_parties`.

**Where it lives:** the `BOARD_MEMBERS` registry and `BOARD_LAST_VERIFIED` in
`Database Codes/download_STKHDR_Meets/gen_stkhdr_profiles.py`. After editing,
bump `BOARD_LAST_VERIFIED` and **regenerate the manifests** (`gen_stkhdr_manifest.py`)
so the group homepage's bulleted Voting Parties list updates.

As of `2026-06`: Chair **Bill Flores**, Vice Chair **Peggy Heeg**; directors
**Linda Capuano, Julie England, Christopher A. Krummel, Kathleen McAllister,
Bill Mohl, John Swainson**.

**Example (`group_summary` for ROS):**

```json
{
  "overview": "The Reliability and Operations Subcommittee (ROS) reports to TAC and oversees ERCOT system reliability, operations, planning, and protocol revisions in its domain, coordinating a dozen technical working groups.",
  "leadership": "Chair: Sandeep Borkar (promoted from Vice Chair); Vice Chair: Shane Thomas",
  "voting_parties": ["Consumer", "Cooperative", "Independent Generator", "Independent Power Marketer", "Independent Retail Electric Provider", "Investor Owned Utility", "Municipal"],
  "voting_structure": "ERCOT market-segment voting; revision requests and recommendations carried to TAC by majority of segments present."
}
```

## meeting_summary — the individual meeting summary

`meeting_summary` is **unique to one meeting** and drives the meeting homepage's
Quick runs / For the talk view. It answers "what happened at this meeting?"

| Key | Content | Source |
|-----|---------|--------|
| `topics` | Array of the substantive subjects covered — the agenda items minus boilerplate (antitrust, agenda review, minutes approval, adjourn) | Agenda; minutes section headers |
| `debates` | Array of plain-text notes on the key discussions, positions, and points of contention | Minutes (discussion paragraphs); comment documents |
| `voting_outcomes` | Array of `{item, motion, result, for, against, abstain}` — the result of each motion/ballot | Combined ballot `.xls`; "Motion Carries/Fails" lines; approved minutes |

Build `voting_outcomes` and `debates` from **this meeting's own minutes** —
prefer the `APPROVED-Minutes` document whose filename carries this meeting's date
(a folder often also holds the *prior* meeting's draft minutes; match the date so
you summarize the right meeting, and prefer approved over draft). Read motion
lines ("X moved to … The motion carried …") for `voting_outcomes` with real
results (carried/failed, opposing/abstaining counts), and substantive discussion
paragraphs for `debates`. Legacy `.doc` minutes are read via Word (win32com);
PDF minutes are de-wrapped into sentences.

### No verified minutes — summarize from the other documents

A meeting's own approved minutes are produced at the *following* meeting and
back-posted later, so recent meetings frequently have **no verified (date-matched)
minutes** on file. **Do not leave the meeting blank** — instead read through the
other documents in the folder and summarize what went on:

- **`debates`** ← read the readable reports/memos/updates/comments (`.docx`,
  `.pdf`) for substantive discussion sentences, and add the titles of the
  reports, updates, and presentations that were given (agendas, minutes, and
  ballots excluded). The batch implementation is `summarize_from_documents()`.
- **`voting_outcomes`** ← fall back to `ballot_results` (with `null`
  tallies/result, since no minutes confirm the vote).
- **`topics`** ← still from the agenda.

This is a best-effort "what happened" picture from the meeting materials, not the
official record; it is automatically replaced by real debates/outcomes once the
approved minutes are posted and a regeneration runs.

**Example (`meeting_summary` for ROS 2026-06-04):**

```json
{
  "topics": ["Election of 2026 ROS leadership", "ROS revision requests (NOGRR/PGRR/NPRR)", "OTWG, PDCWG, and PLWG working group reports"],
  "debates": ["Tabled NOGRR286 and PGRR146/147 referred back to PLWG", "Large-load interconnection and IBR ride-through items carried over"],
  "voting_outcomes": [
    {"item": "NOGRR273", "motion": "To endorse and forward to TAC", "result": null, "for": null, "against": null, "abstain": null},
    {"item": "Combined Ballot", "motion": "To approve the Combined Ballot as presented", "result": null, "for": null, "against": null, "abstain": null}
  ]
}
```

---

## Steps

1. Identify committee abbreviation and meeting date from the user's request.
2. List all files in `Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/YYYY-MM-DD/`.
3. Populate the `documents` field with the filenames found, **excluding any `.zip` archive (case-insensitive), `.tmp` files, and the manifest** — no zip link ever appears in the content window.
4. Read each document in order of priority: segment reps → agenda → ballot → minutes → WG reports.
5. Build `group_summary` (leadership, voting parties, voting structure, overview) from the group's leadership table in `ERCOT Stakeholder Meetings Links.md` §1 and the ERCOT market-segment model; reuse an existing group profile if leadership is unchanged.
6. Build `meeting_summary` (`topics`, `debates`, `voting_outcomes`) for **this** meeting from the agenda, minutes, and ballot — keep it distinct from `group_summary`.
7. Extract all remaining fields. For `ballot_results`, parse the combined ballot `.xls`; for individual separate ballots, add one entry per file.
8. Infer `meeting_type` from the calendar URL slug if the agenda does not state it explicitly (see `ERCOT Stakeholder Meetings Links.md` §2.3).
9. Ensure `Quick runs/` exists under the meeting date folder.
10. Write the JSON file with 2-space indentation.
11. Report the saved path and list any fields that could not be populated.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Saving to the wrong folder | Always `YYYY-MM-DD/Quick runs/`, not the committee root or project root |
| Wrong file name | Must be `<COMMITTEE>-YYYY-MM-DD Profile.json` — e.g. `ROS-2025-01-09 Profile.json` |
| Skipping `.doc` files | Use win32com for all `.doc` files; python-docx only handles `.docx` |
| Treating a draft ballot as the final ballot | Use the `APPROVED-Minutes` doc to verify vote outcomes if a draft ballot differs |
| Listing `.zip` archives in `documents` | Exclude every `.zip` (case-insensitive) — they never appear in the content window; still list non-zip files you could not read |
| Leaving `group_summary` empty | Always populate leadership + voting parties from the §1 leadership table and the ERCOT market-segment model |
| Mixing the two tiers | `group_summary` = group intro (leadership/voting); `meeting_summary` = this meeting's topics/debates/outcomes. The group view shows the former, the meeting view the latter — keep them distinct |
| Leaving `[]` fields as `null` | Array fields must be `[]` when empty, never `null` |
