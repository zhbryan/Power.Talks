---
name: Set-Paper-Trails-Document-Summary
description: Use when asked to generate or refresh the per-document summary shown in the Paper Trails content window when a submitted document's title is clicked on a market-rules issue (NPRR/SCR/COPMGRR/NOGRR/PGRR/RMGRR). One summary per source document; also covers the title hyperlink and the download button on the issue's "Documents Submitted" list.
trigger: When the user asks about the document-summary view, summarizing a single submitted file for a rule, the per-document content-window panel, or the title-link / download-button on an issue's Documents Submitted list.
---

# Set Paper Trails Document Summary

## Overview

Every market-rules issue lists the **documents submitted so far** for that
revision request (its `source_documents`). On the item-rule "Quick runs" card
each document is a row with two controls:

- **Title link** → opens a concise summary of *that one document* in the center
  **content window** (the same pane the issue Summary detail view uses).
- **Download button** → downloads the **original** document to the user's machine.

This skill generates the per-document **summary JSON** the content window fetches.
It is the document-level companion to the issue-level `ERCOT-Market-Rules-Summarization-and-Timeline`
skill — one JSON per submitted file, not per issue.

## Scope

All six categories: `NPRR`, `SCR`, `COPMGRR`, `NOGRR`, `PGRR`, `RMGRR`
(COPMGRR IDs zero-padded to 3 digits, e.g. `COPMGRR015`).

## Input

- **Category** · **Issue ID** · **document filename** (one of the issue's `source_documents`).

## Source and output locations

```
Original document:
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/<filename>

Document summary JSON (this skill writes):
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/Quick runs/Doc Summaries/<safe-name>.json
```

`<safe-name>` = the original filename with its extension swapped for `.json`,
Windows-sanitized. Create `Quick runs/Doc Summaries/` if absent. The content
window fetches the JSON at the %-encoded URL of that path.

## Reading strategy (same as the profile skill)

| Extension | Method |
|-----------|--------|
| `.docx` | `python-docx` paragraphs + tables |
| `.doc`  | `win32com` Word `Content.Text` |
| `.pdf`  | `pdfplumber` text |
| `.xls`  | `xlrd` cells |
| `.xlsx` | `openpyxl` cells |
| `.pptx` | `python-pptx` slide text (if available; else summarize from the title) |

## Summary JSON schema

```json
{
  "document": "1264NPRR-19 ERCOT Comments 031125.docx",
  "issue": "NPRR1264",
  "category": "NPRR",
  "doc_type": "Comments",
  "date": "2025-03-11",
  "author": "ERCOT",
  "summary": "2–4 sentence plain-English summary of what this document says and why it was filed.",
  "key_points": ["…", "…"],
  "download_url": "/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR/NPRR1264/1264NPRR-19%20ERCOT%20Comments%20031125.docx"
}
```

- `doc_type` — infer from filename/content: `Impact Analysis` · `Comments` ·
  `Report` (PRS/ROS/TAC/Board) · `Ballot` · `Markup/Redline` · `Presentation` ·
  `Revision Request` · `As-Built` · `Other`.
- `date` — from the filename date token or the document; else `null`.
- `author` — filing entity/company (e.g. `ERCOT`, `Vistra`, `LCRA`) or `null`.
- `download_url` — the %-encoded path to the **original** file; the download
  button uses it directly. Use `null` only if the file is missing.
- Use `null` for unknown scalars, `[]` for empty arrays.

## Steps

1. Resolve `<CAT>` / `<ISSUE_ID>` / `<filename>`.
2. Read the document text per the strategy above.
3. Classify `doc_type`; pull `date` and `author` from the filename/content.
4. Write a 2–4 sentence `summary` and 2–6 `key_points` — about **this document
   only**, not the whole issue.
5. Set `download_url` to the %-encoded path of the original file.
6. Ensure `Quick runs/Doc Summaries/` exists; write `<safe-name>.json` (2-space indent).
7. Report the saved path; list any field left `null`.

## Batch / refresh

Generate a summary for **each** entry in the issue's `source_documents`
(`Profile.json`). Re-run for a document when a newer version is downloaded
(match by filename). The implementation can live alongside the other generators
in `Database Codes/` (e.g. `gen_mkt_doc_summaries.py`) and reuse the profile
skill's readers.

## How it surfaces (cross-skill)

- **`Set-Paper-Trails-Item-Rule-Homepage`** — renders the "Documents Submitted"
  list: each row is the title link + download button.
- **`Set-Paper-Trails-Homepage`** — the center **content window** renders this
  summary JSON when a title link is clicked ("Document Summary view").

## Common mistakes

| Mistake | Fix |
|---|---|
| Saving outside `Quick runs/Doc Summaries/` | The content window 404s — use the exact path |
| Summarizing the whole issue | Summarize the single document; the issue summary is a different skill |
| Un-encoded `download_url` | %-encode spaces and special characters so the browser fetches the right file |
| Missing `doc_type`/`date` | Best-effort from filename + content; `null` only when truly unavailable |
