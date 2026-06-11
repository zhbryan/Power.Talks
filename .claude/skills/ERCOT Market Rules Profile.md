---
name: ERCOT-Market-Rules-Profile
description: Use when asked to create, build, generate, update, or refresh a profile or summary JSON for any ERCOT market rules revision request — NPRR, NOGRR, PGRR, RMGRR, SCR, or COPMGRR. Also covers detecting issues whose profiles are stale because new documents were downloaded.
---

# ERCOT Market Rules Profile Creator

## Overview

Creates and maintains a structured JSON profile file for any ERCOT market rules revision request, extracting all key metadata from the issue's downloaded documents. The output is saved under the issue's own folder in a `Quick runs` sub-folder.

Two modes:
- **Create mode** — build a profile from scratch for one issue (original behavior).
- **Update mode** — scan the database for issues that received new documents since their profile was written (e.g. after a downloader run), then refresh only those profiles. See **Update Mode** section.

## Scope — All Market Rules Categories

| Abbreviation | Full Name | Governing Document |
|---|---|---|
| `NPRR` | Nodal Protocol Revision Request | Nodal Protocols |
| `NOGRR` | Nodal Operating Guide Revision Request | Nodal Operating Guide |
| `PGRR` | Planning Guide Revision Request | Planning Guide |
| `RMGRR` | Retail Market Guide Revision Request | Retail Market Guide |
| `SCR` | System Change Request | ERCOT Systems / IT |
| `COPMGRR` | Congestion Offset Payment Mechanism Guide Revision Request | COPM Bilateral Agreement |

## Input

- **Category** — one of the abbreviations above, e.g. `NPRR`
- **Issue number** — integer, e.g. `1176` for NPRR or `15` for COPMGRR

## Output Location

```
Documents Database/ERCOT.MKT.RULES/<CATEGORY>/<ISSUE_ID>/Quick runs/<ISSUE_ID> Profile.json
```

- `<ISSUE_ID>` formatting rules — see **Issue ID Format** section below.
- Create `Quick runs/` if it does not already exist.
- File name: `<ISSUE_ID> Profile.json` — e.g. `NPRR1176 Profile.json`, `COPMGRR015 Profile.json`.

## Issue ID Format

| Category | Format | Example |
|---|---|---|
| NPRR | `NPRR{n}` | `NPRR1176` |
| NOGRR | `NOGRR{n}` | `NOGRR272` |
| PGRR | `PGRR{n}` | `PGRR100` |
| RMGRR | `RMGRR{n}` | `RMGRR150` |
| SCR | `SCR{n}` | `SCR800` |
| COPMGRR | `COPMGRR{n:03d}` (zero-padded 3 digits) | `COPMGRR015` |

---

## Profile Fields

Extract the following fields from the issue documents. Use `null` for any field not found; use `[]` for empty arrays.

| # | JSON Key | Source |
|---|---|---|
| 1 | `category` | Category abbreviation (from user input) |
| 2 | `issue_id` | Formatted issue ID string (see Issue ID Format) |
| 3 | `issue_number` | Integer issue number |
| 4 | `title` | Full title of the revision request |
| 5 | `date_posted_decision` | Date Posted or Decision date (ISO 8601: YYYY-MM-DD) |
| 6 | `timeline_requested_resolution` | Requested Resolution date or milestone |
| 7 | `status` | Current status: `Pending` / `Approved` / `Withdrawn` / `Rejected` |
| 8 | `effective_date` | Effective date of the revision (ISO 8601 or null) |
| 9 | `governing_document_sections` | Array of section identifiers in the governing document (see category notes below) |
| 10 | `related_documents_requiring_revision` | Array of related document names or IDs also requiring change |
| 11 | `revision_description` | Plain-text summary of what is being revised |
| 12 | `reason_for_revision` | Why the revision is needed |
| 13 | `business_case` | Business justification or impact statement |
| 14 | `sponsor_name` | Full name of the sponsor |
| 15 | `sponsor_email` | Sponsor email address |
| 16 | `sponsor_company` | Sponsor's organization or company |
| 17 | `sponsor_phone` | Sponsor phone number (string) |
| 18 | `market_segment` | Market segment(s) affected (string or array) |

### Maintenance Fields (required on every create and update)

| JSON Key | Contents |
|---|---|
| `timeline` | Array of `{"date": "YYYY-MM-DD", "event": "...", "doc": "..."}` — one entry per milestone document (posting, ballots, reports, comments, impact analysis, Board/PUCT actions), sorted by date ascending |
| `source_documents` | Array of all document filenames in the issue folder that the profile reflects. This is how Update mode detects new documents — always set it to the full current folder listing when writing a profile. |
| `profile_last_updated` | ISO 8601 timestamp (`YYYY-MM-DDTHH:MM:SS`) of when the profile was last written |

### Category-Specific Notes for `governing_document_sections`

| Category | What this field contains |
|---|---|
| NPRR | Protocol section numbers, e.g. `["Section 2", "Section 6.4.2"]` |
| NOGRR | Nodal Operating Guide section numbers |
| PGRR | Planning Guide section numbers |
| RMGRR | Retail Market Guide section numbers |
| SCR | System/functional area identifiers, e.g. `["MIS", "NMMS", "EMS"]` |
| COPMGRR | COPM Bilateral Agreement section identifiers |

## JSON Template

```json
{
  "category": null,
  "issue_id": null,
  "issue_number": null,
  "title": null,
  "date_posted_decision": null,
  "timeline_requested_resolution": null,
  "status": null,
  "effective_date": null,
  "governing_document_sections": [],
  "related_documents_requiring_revision": [],
  "revision_description": null,
  "reason_for_revision": null,
  "business_case": null,
  "sponsor_name": null,
  "sponsor_email": null,
  "sponsor_company": null,
  "sponsor_phone": null,
  "market_segment": null,
  "timeline": [],
  "source_documents": [],
  "profile_last_updated": null
}
```

---

## Document Type Reference

Each issue folder follows the same document naming convention regardless of category.

| Pattern in filename | Content |
|---|---|
| `-01` main doc | Revision text, reason, business case, sponsor, sections affected |
| `-02` / `-10` Impact Analysis | Cost/budget, time, staffing, system and business function impacts |
| `PRS_Ballot` (`.xls`) | PRS vote record — motion text and outcome |
| `PRS_Report` (`.doc`) | PRS meeting summary — discussions, concerns, modifications |
| `ERCOT_Comments` (`.doc`) | ERCOT staff position and technical clarifications |
| `TAC_Ballot` (`.xls`) | TAC vote record — motion text and outcome |
| `TAC_Report` (`.doc`) | TAC meeting summary — final committee recommendation |
| `Board_Report` (`.doc`) | Board action — approval, deferral, or denial |
| `PUCT_Report` (`.doc`) | Regulatory filing to the Public Utility Commission of Texas |

## Reading Strategy

| Extension | Method |
|---|---|
| `.docx` | `python-docx`: `Document(path)` — read `.paragraphs` and `.tables` |
| `.doc` | `win32com.client`: open with `Word.Application`, read `.Content.Text` |
| `.xls` | Binary string extraction — search for motion text and vote counts |
| `.xlsx` | `openpyxl`: `load_workbook(path, read_only=True, data_only=True)` |

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
motion_lines = [s for s in strings if "motion" in s.lower() or category.lower() in s.lower()]
```

---

## Update Mode — Detecting New Documents and Refreshing Profiles

Run this after any downloader run (see `ERCOT_Market_Rules_Downloader` skill) or whenever asked to "update/refresh profiles".

### Step 1 — Detect stale profiles

```bash
python "Database Codes/profile_MKT_Rules/find_stale_profiles.py"
```

The script scans every issue folder under `Documents Database/ERCOT.MKT.RULES/<CATEGORY>/` and reports, as JSON:

- **`missing`** — issue folders that have documents but no `Quick runs/<ISSUE_ID> Profile.json` at all.
- **`stale`** — profiles whose issue folder contains documents not listed in the profile's `source_documents` array. For legacy profiles without `source_documents`, it falls back to comparing document file mtimes against the profile file's mtime.

Each entry lists the exact new document filenames, so only those need to be read.

### Step 2 — Refresh each flagged profile

For **missing** profiles: run Create mode (full extraction, all fields).

For **stale** profiles, read only the new documents and update incrementally:

1. Append a `timeline` entry per new document (date from the `MMDDYY` suffix in the filename → `20YY-MM-DD`; event from the document type, e.g. `ROS Ballot`, `TAC Report`, `ERCOT Comments`). Keep the array sorted by date; never duplicate an existing entry.
2. Re-evaluate status-bearing documents — a `TAC Report`, `Board_Report`, or `PUCT_Report` may change `status` (e.g. `Pending` → `Approved`) and `effective_date`. Read the report text to confirm the outcome; do not infer approval from the filename alone.
3. Leave all other fields untouched unless a new document explicitly revises them (e.g. revised sponsor, retitled request).
4. Set `source_documents` to the full current folder listing and refresh `profile_last_updated`.

### Step 3 — Report

Summarize per category: profiles created, profiles updated, and any status changes (issue → old status → new status).

---

## Steps

1. Identify the category and issue number from the user's request or document filenames.
2. Construct `issue_id` using the format table above.
3. Read the primary `-01` document and any supporting documents in the issue folder.
4. Extract all 18 fields. For array fields, produce a JSON array; use `[]` if none found.
5. Normalize dates to ISO 8601 (`YYYY-MM-DD`). Use a descriptive string only when no calendar date is available.
6. Build the maintenance fields: `timeline` from the documents found, `source_documents` from the full folder listing, `profile_last_updated` from the current time.
7. Ensure `Quick runs/` exists under `Documents Database/ERCOT.MKT.RULES/<CATEGORY>/<ISSUE_ID>/`.
8. Write the JSON file with 2-space indentation.
9. Report the saved file path and list any fields that could not be populated.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using the wrong issue ID format | COPMGRR zero-pads to 3 digits (`COPMGRR015`); all others use plain integers |
| Saving to the wrong folder | Always `<ISSUE_ID>/Quick runs/`, not the category root or project root |
| Skipping `.doc` files | Use win32com for all `.doc` files; python-docx only reads `.docx` |
| Leaving dates as raw text | Normalize to `YYYY-MM-DD`; use a string only when no date is available |
| Omitting empty arrays | Use `[]` for array fields with no data, never omit or use `null` |
| Forgetting `source_documents` when writing a profile | Update mode relies on it — always set it to the full current folder listing on every write |
| Changing `status` from a ballot/report filename alone | Read the report text; only TAC/Board/PUCT outcomes change status, and reports can table or remand an issue |
