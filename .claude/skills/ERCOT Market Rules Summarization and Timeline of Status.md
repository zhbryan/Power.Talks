---
name: ERCOT-Market-Rules-Summarization-and-Timeline
description: Use when asked to summarize any ERCOT market rules revision request, analyze its background and impacts, or produce a stakeholder timeline report — covers NPRR, NOGRR, PGRR, RMGRR, SCR, and COPMGRR.
---

# ERCOT Market Rules Summarization and Timeline of Status

## Overview

Reads all documents in an ERCOT market rules issue folder, synthesizes the revision's main ideas and potential impacts, and reconstructs the full ERCOT stakeholder discussion timeline. Outputs a `.docx` report saved to the issue's `Quick runs` sub-folder.

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

- **Category** — e.g. `NPRR`
- **Issue number** — e.g. `1176`

## Output Location

```
Documents Database/ERCOT.MKT.RULES/<CATEGORY>/<ISSUE_ID>/Quick runs/<ISSUE_ID> Summary.docx
```

Create `Quick runs/` if it does not exist. Issue ID formatting follows the same rules as the Profile skill (COPMGRR zero-pads to 3 digits; all others are plain integers).

---

## Document Type Reference

All categories share the same document naming convention. Read every file present; use only what is relevant to each report section.

| Pattern in filename | Content |
|---|---|
| `-01` main doc | Revision text, reason, business case, sponsor, governing document sections |
| `-02` / `-10` Impact Analysis | Cost/budget, time, staffing, system and business function impacts |
| `PRS_Ballot` (`.xls`) | PRS vote record — extract motion text and outcome |
| `PRS_Report` (`.doc`) | PRS meeting summary — discussions, concerns, modifications proposed |
| `ERCOT_Comments` (`.doc`) | ERCOT staff position and technical clarifications |
| `TAC_Ballot` (`.xls`) | TAC vote record — extract motion text and outcome |
| `TAC_Report` (`.doc`) | TAC meeting summary — final committee recommendation |
| `Board_Report` (`.doc`) | Board action — approval, deferral, or denial |
| `PUCT_Report` (`.doc`) | Regulatory filing to the Public Utility Commission of Texas |

---

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

**For `.xls` ballot files (vote extraction):**
```python
import re
with open(path, "rb") as f:
    data = f.read()
strings = [s.decode("ascii", errors="ignore") for s in re.findall(rb"[\x20-\x7e]{10,}", data)]
motion_lines = [s for s in strings if "motion" in s.lower() or issue_id.lower() in s.lower()]
```

---

## Step-by-Step Execution

### Step 1 — Gather documents

List all files in `Documents Database/ERCOT.MKT.RULES/<CATEGORY>/<ISSUE_ID>/` and sort by document sequence number (the `NN` in `<ISSUE_ID>-NN`).

### Step 2 — Extract core content

Read the `-01` document first. Extract:
- Revision description
- Reason(s) for revision (checkboxes or stated rationale)
- Business case narrative
- Governing document sections being revised
- Sponsor name, company, email, phone
- Market segment

If a `<ISSUE_ID> Profile.json` already exists in `Quick runs/`, load it instead of re-extracting — it contains all fields pre-parsed.

### Step 3 — Extract impact analysis

Read the `-02` document (and any revised impact analysis, e.g. `-10`). Extract:
- Estimated cost / budgetary impact
- Estimated time and project requirements
- ERCOT system and staffing impacts
- Notable comments

Use the most recent impact analysis if multiple versions exist.

### Step 4 — Build the stakeholder timeline

For each PRS, TAC, and Board document in date order:

| Document | What to extract |
|---|---|
| PRS Ballot | Motion text, vote count (For / Against / Abstain), pass or fail |
| PRS Report | Key stakeholder concerns, ERCOT responses, any language modifications |
| ERCOT Comments | ERCOT's stated position and any proposed changes |
| TAC Ballot | Motion text, vote count, pass or fail |
| TAC Report | TAC recommendation (approve / modify / remand) |
| Board Report | Final board action and effective date if stated |
| PUCT Report | Whether PUCT review was required; outcome if available |

For each entry, record: **Date · Body · Action · Outcome**.

### Step 5 — Determine current status

Infer from the latest document in the folder:

| Latest document present | Status inference |
|---|---|
| Board Report | **Approved** (or Withdrawn/Rejected per board text) |
| TAC Report only | **At Board** or **Pending Board Action** |
| PRS Reports only | **At TAC** or **In PRS Review** |
| Only `-01` | **Recently Posted / Pending PRS** |

### Step 6 — Write the Summary report

Use `python-docx` to produce the `.docx` file. Structure:

```
<ISSUE_ID> — <Title>
Summary Report
────────────────────────────────────────────
1. Executive Summary
   - What is being revised (1–2 sentences)
   - Why it matters (background context)
   - Key potential impacts on market participants

2. Issue Details
   - Status  |  Date Posted  |  Requested Resolution
   - Governing Document Sections Revised
   - Sponsor

3. Impact Analysis
   - Budgetary / cost impact
   - System / staffing impacts
   - Implementation timeline

4. Stakeholder Discussion Timeline
   [Date]  [Body]  [Action]  [Outcome / Notes]
   ... one row per meeting event, chronological

5. Current Status
   - Plain-language statement of where the issue stands today
   - Next expected step (if pending)
```

**python-docx skeleton:**
```python
from docx import Document
from docx.shared import Pt
import os

doc = Document()
doc.add_heading(f"{issue_id} — {title}", level=1)

def section(doc, heading, body_lines):
    doc.add_heading(heading, level=2)
    for line in body_lines:
        doc.add_paragraph(line)

table = doc.add_table(rows=1, cols=4)
table.style = "Table Grid"
hdr = table.rows[0].cells
hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "Date", "Body", "Action", "Outcome"
for event in timeline_events:
    row = table.add_row().cells
    row[0].text = event["date"]
    row[1].text = event["body"]
    row[2].text = event["action"]
    row[3].text = event["outcome"]

out_path = os.path.join(folder, "Quick runs", f"{issue_id} Summary.docx")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
doc.save(out_path)
```

---

## Report Writing Guidelines

- **Executive Summary**: Write for a non-technical reader. State what rule or guide section is changing, what problem it solves, and who is affected (Market Participants, ERCOT operations, specific resource types, etc.).
- **Background**: Reference the triggering event when available — PUCT directives, NERC standards, prior incidents, or ERCOT strategic plan items.
- **Potential Impacts**: Distinguish between operational impacts (how ERCOT or MPs change behavior), financial impacts (settlement, cost allocation), and system/IT impacts.
- **Timeline narrative**: Each meeting entry should be one factual sentence: what body met, what motion was made, and whether it passed.
- **Current status**: One clear sentence. If approved, state whether it is pending implementation. If pending, state the next decision body.

### Category-Specific Notes

| Category | Additional context to include |
|---|---|
| NPRR | Note which protocol sections change and whether PUCT approval was required |
| NOGRR | Note operational procedures affected; distinguish from protocol-level changes |
| PGRR | Note planning criteria or interconnection study methodology changes |
| RMGRR | Note retail settlement or metering rule changes |
| SCR | Note which ERCOT systems are affected; implementation window if stated |
| COPMGRR | Note COPM Bilateral Agreement section and effect on COPM settlement |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Skipping `.doc` files | Use win32com for all `.doc` files; python-docx only handles `.docx` |
| Treating PRS/TAC ballots as reports | Ballots are vote records only; narrative is in the paired Report doc |
| Ignoring PRS/TAC reports | They contain stakeholder concerns and language modifications — essential for the timeline |
| Writing the timeline from filenames alone | Always read the Report documents; filenames give dates but not outcomes |
| Wrong output path | Must be `<ISSUE_ID>/Quick runs/<ISSUE_ID> Summary.docx`, not the category root |
| Missing dependencies | `pip install python-docx pywin32` |
