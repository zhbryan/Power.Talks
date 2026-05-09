---
name: ERCOT-Stakeholder-Meeting-Profile
description: Use when asked to create, build, or generate a profile or summary JSON for a specific ERCOT stakeholder committee meeting (ROS, TAC, PRS, WMS, RMS, Board, or any active subgroup).
---

# ERCOT Stakeholder Meeting Profile Creator

## Overview

Creates a structured JSON profile file for a specific ERCOT stakeholder committee meeting, extracting key metadata from the meeting documents already downloaded to the local folder. The output file is saved in a `Quick runs` sub-folder under the meeting date folder.

## Scope — Active Committees

This skill applies to all in-scope committees listed in `ERCOT_Stakeholder_Meetings_Links.md`. Use the exact abbreviations from that file:

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
| `meeting-materials` / `Meeting-Materials` | Materials bundle (`.zip`) | Note presence only |
| `Revision-Request` / `revision-request` | Revision request bundle (`.zip`) | Note presence only |

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

## Profile Fields

Extract the following fields. Use `null` for any field not found; use `[]` for empty arrays.

| # | JSON Key | Source |
|---|----------|--------|
| 1 | `committee` | Committee abbreviation (from user input) |
| 2 | `committee_full_name` | Full name from `ERCOT_Stakeholder_Meetings_Links.md` |
| 3 | `meeting_date` | ISO 8601 date (YYYY-MM-DD) |
| 4 | `meeting_type` | `Regular` / `WebEx` / `Email Vote` / `Special` / `Joint` / `Info Session` — infer from calendar URL slug or agenda text |
| 5 | `calendar_url` | `https://www.ercot.com/calendar/MMDDYYYY-<SLUG>` |
| 6 | `chair` | From segment reps doc or agenda opening |
| 7 | `vice_chair` | From segment reps doc or agenda opening |
| 8 | `agenda_items` | Array of agenda item title strings, in order |
| 9 | `ballot_results` | Array of `{item, motion, for, against, abstain, result}` objects from ballot `.xls` |
| 10 | `working_group_reports` | Array of WG abbreviations that submitted a report (e.g. `["NDSWG", "PLWG", "DWG"]`) |
| 11 | `key_discussion_topics` | Array of plain-text topic summaries from minutes |
| 12 | `action_items` | Array of action items from minutes |
| 13 | `documents` | Array of all filenames present in the meeting folder |
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

---

## Steps

1. Identify committee abbreviation and meeting date from the user's request.
2. List all files in `Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/YYYY-MM-DD/`.
3. Populate the `documents` field with all filenames found.
4. Read each document in order of priority: segment reps → agenda → ballot → minutes → WG reports.
5. Extract all fields. For `ballot_results`, parse the combined ballot `.xls`; for individual separate ballots, add one entry per file.
6. Infer `meeting_type` from the calendar URL slug if the agenda does not state it explicitly (see `ERCOT_Stakeholder_Meetings_Links.md` §2.3).
7. Ensure `Quick runs/` exists under the meeting date folder.
8. Write the JSON file with 2-space indentation.
9. Report the saved path and list any fields that could not be populated.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Saving to the wrong folder | Always `YYYY-MM-DD/Quick runs/`, not the committee root or project root |
| Wrong file name | Must be `<COMMITTEE>-YYYY-MM-DD Profile.json` — e.g. `ROS-2025-01-09 Profile.json` |
| Skipping `.doc` files | Use win32com for all `.doc` files; python-docx only handles `.docx` |
| Treating a draft ballot as the final ballot | Use the `APPROVED-Minutes` doc to verify vote outcomes if a draft ballot differs |
| Omitting the `documents` field | Always list all files present, even ZIPs and files you could not read |
| Leaving `[]` fields as `null` | Array fields must be `[]` when empty, never `null` |
