---
name: COPMBRR-Summarization-and-Timeline
description: Use when asked to summarize a COPMBRR, analyze its background and impacts, or produce a stakeholder timeline report for a COPMBRR document set.
---

# COPMBRR Summarization and Timeline of Status

## Overview

Reads all documents in a COPMBRR folder, synthesizes the revision's main ideas and potential impacts, and reconstructs the full ERCOT stakeholder discussion timeline. Outputs a `.docx` report saved to the COPMBRR's `Quick runs` sub-folder.

## Output Location

```
Documents Database/ERCOT.MKT.RULES/COPMBRR/COPMBRR<number>/Quick runs/COPMBRR<number> Summary.docx
```

Create `Quick runs/` if it does not exist.

---

## Document Type Reference

Each document in the COPMBRR folder has a distinct role. Read them all; use only what is relevant to each report section.

| Pattern in filename | Content |
|---------------------|---------|
| `-01` main doc      | Revision text, reason, business case, sponsor, agreement sections |
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

Different file formats require different Python tools.

| Extension | Method |
|-----------|--------|
| `.docx`   | `python-docx`: `Document(path)` — read `.paragraphs` and `.tables` |
| `.doc`    | `win32com.client`: open with `Word.Application`, read `.Content.Text` |
| `.xls`    | Binary string extraction — search for motion text and vote counts |
| `.xlsx`   | `openpyxl`: `load_workbook(path, read_only=True, data_only=True)` |

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
motion_lines = [s for s in strings if "motion" in s.lower() or "copmbrr" in s.lower()]
```

---

## Step-by-Step Execution

### Step 1 — Gather documents

List all files in `Documents Database/ERCOT.MKT.RULES/COPMBRR/COPMBRR<number>/` and sort by document sequence number (the `NN` in `COPMBRRxx-NN`).

### Step 2 — Extract core content

Read the `-01` document first. Extract:
- Revision description
- Reason(s) for revision (checkboxes selected)
- Business case narrative
- Agreement sections revised
- Sponsor name, company, email, phone
- Market segment

If a `COPMBRR<number> Profile.json` already exists in `Quick runs/`, load it instead of re-extracting — it contains all fields pre-parsed.

### Step 3 — Extract impact analysis

Read the `-02` (and any revised impact analysis, e.g. `-10`). Extract:
- Estimated cost / budgetary impact
- Estimated time and project requirements
- ERCOT system and staffing impacts
- Notable comments

Use the most recent impact analysis if multiple versions exist.

### Step 4 — Build the stakeholder timeline

For each PRS, TAC, and Board document (in date order):

| Document | What to extract |
|----------|----------------|
| PRS Ballot | Motion text, vote count (For / Against / Abstain), pass or fail |
| PRS Report | Key stakeholder concerns, ERCOT responses, any agreement language modifications |
| ERCOT Comments | ERCOT's stated position and any proposed changes |
| TAC Ballot | Motion text, vote count, pass or fail |
| TAC Report | TAC recommendation (approve / modify / remand) |
| Board Report | Final board action and effective date if stated |
| PUCT Report | Whether PUCT review was required; outcome if available |

For each meeting entry, record: **Date · Body · Action · Outcome**.

### Step 5 — Determine current status

Infer from the latest document in the folder:
- If Board Report exists → **Approved** (or Withdrawn/Rejected per board text)
- If TAC Report exists but no Board Report → **At Board** or **Pending Board Action**
- If PRS Reports exist but no TAC → **At TAC** or **In PRS Review**
- If only `-01` exists → **Recently Posted / Pending PRS**

### Step 6 — Write the Summary report

Use `python-docx` to produce the `.docx` file. Structure:

```
COPMBRR<number> — <Title>
Summary Report
────────────────────────────────────────────
1. Executive Summary
   - What is being revised (1–2 sentences)
   - Why it matters (background context)
   - Key potential impacts on market participants

2. COPMBRR Details
   - Status  |  Date Posted  |  Requested Resolution
   - Agreement Sections Revised
   - Sponsor

3. Impact Analysis
   - Budgetary / cost impact
   - System / staffing impacts
   - Implementation timeline

4. Stakeholder Discussion Timeline
   [Date]  [Body]  [Action]  [Outcome / Notes]
   ... one row per meeting event, chronological

5. Current Status
   - Plain-language statement of where the COPMBRR stands today
   - Next expected step (if pending)
```

**python-docx skeleton:**
```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

doc = Document()

# Title
t = doc.add_heading(f"COPMBRR{n} — {title}", level=1)

# Section helper
def section(doc, heading, body_lines):
    doc.add_heading(heading, level=2)
    for line in body_lines:
        doc.add_paragraph(line)

# Timeline table
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

out_path = os.path.join(folder, "Quick runs", f"COPMBRR{n} Summary.docx")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
doc.save(out_path)
```

---

## Report Writing Guidelines

- **Executive Summary**: Write for a non-technical reader. State what agreement term is changing, what problem it solves, and who is affected (Market Participants, ERCOT operations, CRR holders, etc.).
- **Background**: Reference the triggering event when available — PUCT directives, NERC standards, prior incidents, or ERCOT strategic plan items.
- **Potential Impacts**: Distinguish between operational impacts (how ERCOT or MPs change their behavior), financial impacts (COPM settlement, cost allocation), and system/IT impacts.
- **Timeline narrative**: Each meeting entry should be one factual sentence: what body met, what motion was made, and whether it passed.
- **Current status**: One clear sentence. If approved, state whether it is pending implementation. If pending, state the next decision body.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Skipping `.doc` files because they can't be opened with python-docx | Use win32com for all `.doc` files |
| Treating PRS/TAC ballots as reports | Ballots are vote records only; narrative is in the paired Report doc |
| Using only the `-01` doc and ignoring PRS/TAC reports | PRS and TAC reports contain stakeholder concerns and agreement modifications — essential for the timeline |
| Writing the timeline from filenames alone | Always read the Report documents; filenames give the date but not the outcome |
| Saving as `.docx` to the wrong path | Must be `COPMBRR<number>/Quick runs/COPMBRR<number> Summary.docx` — not the root folder |
| python-docx or pywin32 missing | `pip install python-docx pywin32` |
