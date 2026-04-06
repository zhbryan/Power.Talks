---
name: default-studies
description: Instructs Claude to analyze and summarize ERCOT documents into structured Word reports saved to Reports Database/.
trigger: When the user invokes /default-studies, or when study.py requests document summarization.
---

# Default Studies Skill

You are analyzing an ERCOT regulatory document for the **Power.Talks** project.

## Output Structure

Produce a structured report with exactly these sections:

### 1. Document Title & Date
State the full document title and its publication or effective date.

### 2. Executive Summary
Write 3–5 sentences capturing the document's core purpose and most important outcome.

### 3. Key Points
Bullet list of the most significant facts, rule changes, or decisions in the document.

### 4. Market Impact
Describe who is affected (Market Participants, QSEs, TSPs, REPs, etc.) and how. Be specific about operational or financial implications.

### 5. Action Items & Deadlines
List any compliance requirements, filing deadlines, or implementation milestones. If none, state "No action items identified."

## Formatting Rules
- Use clear, plain business English — avoid jargon where possible
- Each section heading must appear exactly as shown above
- Keep bullet points concise (one idea per bullet)
- Dates must be in MM/DD/YYYY format

## Output Destination
- Save the report as a `.docx` file to `Reports Database/`
- Filename format: `<CATEGORY>_<DOCUMENT_NAME>_<YYYYMMDD>.docx`
  - Example: `NPRR_NPRR1234_20260405.docx`
  - Example: `BOARD_BoardMeeting_20260405.docx`
