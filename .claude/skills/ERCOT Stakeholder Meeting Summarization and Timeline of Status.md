---
name: ERCOT-Stakeholder-Meeting-Summarization-and-Timeline
description: Use when asked to summarize a committee's meeting history, analyze discussion trends, or produce a timeline report for any active ERCOT stakeholder committee (ROS, TAC, PRS, WMS, RMS, Board, or any active subgroup).
---

# ERCOT Stakeholder Meeting Summarization and Timeline of Status

## Overview

Reads all documents in a committee's local meeting folders across a date range, synthesizes recurring themes and key votes, and reconstructs a chronological timeline of meetings. Outputs a `.docx` report saved to a `Quick runs` sub-folder at the committee root.

## Scope — Active Committees

Applies to all in-scope committees in `ERCOT Stakeholder Meetings Links.md`:

`Board` · `FA` · `HRG` · `TS` · `TAC` · `LLWG` · `CFSG` · `RTCBTF` · `PRS` · `RMS` · `TDTMS` · `RMTTF` · `ROS` · `IBRWG` · `BSWG` · `DWG` · `MWG` · `NDSWG` · `OWG` · `OTWG` · `PDCWG` · `PLWG` · `SPWG` · `SSWG` · `VPWG` · `WMS` · `CMWG` · `DSWG` · `SAWG` · `WMWG` · `IBRTF`

## Input

- **Committee abbreviation** — e.g. `ROS`
- **Date range** — e.g. `2024-2025` or `all` (default: all folders present locally)

## Output Location

```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/Quick runs/<COMMITTEE> Summary <YYYY>-<YYYY>.docx
```

- Create `Quick runs/` at the committee root if it does not exist.
- File name format: `<COMMITTEE> Summary YYYY-YYYY.docx` — e.g. `ROS Summary 2010-2025.docx`.
- If only a single year is requested: `ROS Summary 2025.docx`.

---

## Source Folders

```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/
    YYYY-MM-DD/          ← one folder per meeting date
        <documents>
    Quick runs/          ← output target
```

If a `<COMMITTEE>-YYYY-MM-DD Profile.json` exists in any meeting's `Quick runs/` sub-folder, load it to avoid re-parsing those documents.

---

## Document Type Reference

| Filename keyword(s) | Content to extract |
|---------------------|--------------------|
| `agenda` | Meeting date, agenda items, chair noted in opening |
| `APPROVED-Minutes` / `minutes` | Key discussion topics, action items, vote outcomes confirmed |
| `combined-ballot` / `ballot` | Ballot items and vote counts |
| `segment_representative` | Chair / Vice Chair for that meeting |
| `_report_to_` / `Report-to-` | Which WGs submitted reports; topic of report |

---

## Reading Strategy

| Extension | Method |
|-----------|--------|
| `.docx` | `python-docx`: `Document(path)` — `.paragraphs` and `.tables` |
| `.doc`  | `win32com.client`: `Word.Application`, `.Content.Text` |
| `.xls`  | Binary string extraction for vote counts and motion text |
| `.xlsx` | `openpyxl`: `load_workbook(path, read_only=True, data_only=True)` |
| `.pptx` | `python-pptx`: iterate slides and text frames |

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

---

## Step-by-Step Execution

### Step 1 — Discover meeting folders

List all `YYYY-MM-DD` sub-folders in `Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/`. Filter to the requested date range. Sort chronologically.

```python
import os, re
from datetime import date

ROOT = rf"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS\{committee}"
date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
folders = sorted(
    f for f in os.listdir(ROOT)
    if date_pattern.match(f) and year_start <= int(f[:4]) <= year_end
)
```

### Step 2 — Load or parse each meeting

For each meeting folder, in date order:

1. If `Quick runs/<COMMITTEE>-YYYY-MM-DD Profile.json` exists → load it (all fields pre-parsed).
2. Otherwise → read documents in this priority: segment reps → agenda → ballot → minutes → WG reports.
3. Extract: meeting type, chair, vice chair, agenda items, ballot results, key discussion topics, WG reports received.

### Step 3 — Build the meeting timeline

Accumulate one entry per meeting:

```python
{
    "date": "2025-01-09",
    "type": "WebEx",
    "chair": "Sandeep Borkar",
    "agenda_items": [...],
    "ballot_results": [...],
    "wg_reports": ["NDSWG", "PLWG", "DWG"],
    "key_topics": [...],
    "action_items": [...]
}
```

### Step 4 — Compute summary statistics

- Total meetings by year (table: Year | Total | Regular | WebEx | Email Vote | Special | Cancelled)
- Total ballot items voted on across the range
- Most frequently reporting WGs
- Chair/Vice Chair changes over time

### Step 5 — Determine current status

Based on the most recent meeting folder:
- If minutes are present → **Last Meeting Completed** (state date)
- If only agenda is present → **Meeting Pending** (state date)
- Note next scheduled meeting if mentioned

### Step 6 — Write the Summary report

Use `python-docx`. Structure:

```
<COMMITTEE> — <Full Name>
Meeting Summary Report  YYYY–YYYY
────────────────────────────────────────────
1. Executive Summary
   - Committee purpose (1–2 sentences from ERCOT Stakeholder Meetings Links.md)
   - Date range covered
   - Total meetings included
   - Current chair / vice chair

2. Meeting Counts by Year
   [table: Year | Total | Regular | WebEx | Email Vote | Special | Cancelled]

3. Chronological Meeting Timeline
   [table: Date | Type | Chair | Key Topics | Ballot Items | WG Reports]

4. Ballot / Vote Summary
   - List all ballot items voted on, with final outcome
   - Group by item type (NPRR / NOGRR / PGRR / Procedures / Other)

5. Working Group Reports Received
   - Table: WG | # Reports in range | Most Recent Date

6. Recurring Agenda Topics
   - Bullet list of topics that appeared in 3+ meetings

7. Current Status
   - Most recent completed meeting
   - Next scheduled meeting (if known)
   - Current chair / vice chair
```

**python-docx skeleton:**
```python
from docx import Document
from docx.shared import Pt
import os

doc = Document()
doc.add_heading(f"{committee} — {full_name}", level=1)
doc.add_heading(f"Meeting Summary Report  {year_start}–{year_end}", level=2)

def add_section(doc, title, content_lines):
    doc.add_heading(title, level=2)
    for line in content_lines:
        doc.add_paragraph(line)

# Timeline table
table = doc.add_table(rows=1, cols=6)
table.style = "Table Grid"
hdr = table.rows[0].cells
for i, h in enumerate(["Date", "Type", "Chair", "Key Topics", "Ballots", "WG Reports"]):
    hdr[i].text = h
for entry in timeline:
    row = table.add_row().cells
    row[0].text = entry["date"]
    row[1].text = entry["type"]
    row[2].text = entry["chair"] or ""
    row[3].text = "; ".join(entry["key_topics"][:3])
    row[4].text = ", ".join(b["item"] for b in entry["ballot_results"])
    row[5].text = ", ".join(entry["wg_reports"])

out_path = os.path.join(ROOT, "Quick runs", f"{committee} Summary {year_start}-{year_end}.docx")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
doc.save(out_path)
```

---

## Report Writing Guidelines

- **Executive Summary**: Write for a reader unfamiliar with the committee. State its role in the ERCOT governance process and which parent body it reports to (from `ERCOT Stakeholder Meetings Links.md`).
- **Timeline narrative**: Each meeting entry should be factual and concise — date, what was voted on, which WGs reported, any notable agenda items.
- **Ballot summary**: State the item identifier, a one-sentence description of what was being voted on, and whether it passed.
- **Current status**: One clear sentence on where the committee stands today.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping `.doc` files | Use win32com for all `.doc` files |
| Treating draft minutes as approved | Only mark topics as confirmed outcomes if `APPROVED-Minutes` is present |
| Missing WG report pptx files because they look unimportant | Always scan all `.pptx` files — they contain WG report content |
| Saving the report to the meeting date folder instead of the committee root | Must be `<COMMITTEE>/Quick runs/`, not `<COMMITTEE>/YYYY-MM-DD/Quick runs/` |
| Using only the most recent year | Re-read the user's date range request; default is all folders present locally |
| Missing python-docx or pywin32 | `pip install python-docx python-pptx pywin32` |
