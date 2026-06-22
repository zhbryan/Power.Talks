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
Original documents:
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/<filename>

Where the summaries live (this skill writes):
  the `source_documents` array INSIDE the issue's
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/Quick runs/<ISSUE_ID> Profile.json
```

**Summaries are embedded in the issue `Profile.json` as `source_documents`** —
one entry per submitted file (no separate per-document JSON files). The item-rule
card already fetches `Profile.json`, so it gets the list **and** the summaries in
one request, and the content window renders the entry passed to it on click — no
extra fetch. The batch implementation is `Database Codes/gen_mkt_doc_summaries.py`.

## Reading strategy (same as the profile skill)

| Extension | Method |
|-----------|--------|
| `.docx` | `python-docx` paragraphs + tables |
| `.doc`  | `win32com` Word `Content.Text` |
| `.pdf`  | `pdfplumber` text |
| `.xls`  | `xlrd` cells |
| `.xlsx` | `openpyxl` cells |
| `.pptx` | `python-pptx` slide text (if available; else summarize from the title) |

## `source_documents` entry schema (one per submitted file)

```json
{
  "file": "1264NPRR-19 ERCOT Comments 031125.docx",
  "doc_type": "Comments",
  "date": "2025-03-11",
  "author": "ERCOT",
  "summary": "2–4 sentence plain-English summary of what this document says and why it was filed.",
  "key_points": ["…", "…"],
  "download_url": "/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/NPRR/NPRR1264/1264NPRR-19%20ERCOT%20Comments%20031125.docx"
}
```

`Profile.json["source_documents"]` is the array of these (newest/seq order,
`.zip` excluded).

- `doc_type` — infer from filename/content: `Impact Analysis` · `Comments` ·
  `Report` (PRS/ROS/TAC/Board) · `Ballot` · `Markup/Redline` · `Presentation` ·
  `Revision Request` · `As-Built` · `Other`.
- `date` — from the filename date token or the document; else `null`.
- `author` — filing entity/company (e.g. `ERCOT`, `Vistra`, `LCRA`) or `null`.
- `download_url` — the %-encoded path to the **original** file; the download
  button uses it directly. Use `null` only if the file is missing.
- Use `null` for unknown scalars, `[]` for empty arrays.

## Steps

1. For each issue: list the submitted files (`.zip`/`.tmp` excluded), in seq order.
2. For each file: classify `doc_type`; pull `date`/`author` from the filename
   (and content if reading). Filename-derived is the default (fast, full
   coverage); pass `--read` to also open `.docx/.pdf/.xlsx` for richer `summary`.
3. Write a 2–4 sentence `summary` (and `key_points`) about **this document only**,
   not the whole issue; set `download_url` to the %-encoded original-file path.
4. Set `Profile.json["source_documents"]` to the array of entries and write the
   profile back (2-space indent). Leave the rest of the profile untouched.
5. Report counts.

## Batch / refresh

`gen_mkt_doc_summaries.py` does all issues (or a category subset:
`… NPRR PGRR`). Re-run after a downloader pass so newly submitted files appear.
It only rewrites the `source_documents` field of each `Profile.json`.

## How it surfaces (cross-skill)

- **`Set-Paper-Trails-Homepage`** — the **center content window** owns this: a
  "Documents Submitted" section in each issue detail view (below Current Status)
  lists `source_documents` **sorted by the sequence number after `[rule#][CAT]-`**
  (`1340NPRR-01`, `…-02`, …), each row a title link + download button. Clicking a
  title sets `activeRuleDoc` and renders that entry's summary in the same content
  window (no extra fetch).
- It is **not** on the right-panel Quick-runs card (`Set-Paper-Trails-Item-Rule-Homepage`).

## Common mistakes

| Mistake | Fix |
|---|---|
| Writing separate per-document JSON files | Summaries live in `Profile.json["source_documents"]`; the card already has them |
| Rewriting the whole profile | Only set the `source_documents` field; leave other fields intact |
| Summarizing the whole issue | Summarize the single document; the issue summary is a different skill |
| Un-encoded `download_url` | %-encode spaces/specials so the browser fetches the right file |
