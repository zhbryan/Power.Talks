---
name: Set-Meeting-Tracks-Document-Summary
description: Use when asked to generate or refresh the per-document report shown in the Meeting Tracks content window when a meeting document is clicked on a group homepage — its title, executive summary, download link, and the sponsor/company/meeting/time card in the right panel. One report per source document under Documents Database/ERCOT.STKHDR.MEETS.
trigger: When the user asks about the Meeting Tracks document summary, summarizing a single stakeholder meeting document, the executive summary on a meeting document page, who presented a meeting document, or the per-document content-window panel under Meeting Tracks.
---

# Set Meeting Tracks Document Summary

## Overview

Every ERCOT stakeholder meeting publishes a set of documents (agenda, minutes,
reports, presentations, ballots). Clicking one on a Meeting Tracks **group
homepage** opens a **per-document report** across **both panels** — the Meeting
Tracks counterpart of `Set-Paper-Trails-Document-Summary`. Every document gets
the same template; fields a document lacks render as "—".

- **Center content window** → in this order: **(1) the document title**,
  **(2) its Executive Summary**, **(3) a link that downloads the full
  document**, then the meeting metadata (committee, meeting date, document
  type, and "Presented by" when known).
- **Right panel "For the talk"** → the document card: **Sponsor**, **Company**,
  **Stakeholder Meeting**, **Meeting Time**, under the document's title and
  type badge.
- **No timeline** in this view.

This is the document-level companion to `ERCOT-Stakeholder-Meeting-Profile`
(which summarizes the *meeting*). The batch implementation is
`Database Codes/download_STKHDR_Meets/gen_stkhdr_doc_summaries.py`.

## Scope

All 42 committee folders under `Documents Database/ERCOT.STKHDR.MEETS`, every
meeting date folder, every document the group homepage lists.

## Input

**Committee abbreviation** · **meeting date (ISO)** · **document filename**.

## Source and output locations

```
Original documents:
  Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD>/<filename>

Where the reports live (this skill writes):
  the `document_reports` array INSIDE the meeting's
  Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD>/Quick runs/<COMMITTEE>-<YYYY-MM-DD> Profile.json
```

**Reports are embedded in the meeting `Profile.json`**, like the market-rules
side embeds `source_documents` — one entry per document, no separate
per-document files. The item page and the right-panel card each read that one
file, so opening a document costs a single fetch and no new endpoint.

The generator writes **only** `document_reports` and `meeting_time`; everything
else in the profile belongs to `gen_stkhdr_profiles.py`. That script, in turn,
**carries both fields forward when it rewrites a profile under `--overwrite`** —
they cost AI quota to earn and must survive a profile regeneration.

## Reading strategy

| Extension | Method | Count in tree |
|-----------|--------|---------------|
| `.doc`  | `win32com` Word `Content.Text` | 9,009 |
| `.pptx` | `python-pptx` slide shapes + tables | 8,274 |
| `.docx` | `python-docx` paragraphs + tables | 4,529 |
| `.pdf`  | `pdfplumber` text | 4,083 |
| `.ppt`  | `win32com` PowerPoint `TextFrame` | 3,703 |
| `.xls`  | `xlrd` cells | 2,001 |
| `.xlsx` / `.xlsm` | `openpyxl` cells | 1,288 |

**Presentations are the largest class here** — `.pptx` + `.ppt` outnumber PDFs
two to one — so a reader that skips them leaves most of the meeting record
unread. This is the main difference from the market-rules reader.

Word and PowerPoint are driven through COM and **recycled every 40 opens**: a
long-lived Office instance starts truncating documents and leaking memory.

`.zip`, `.extracted`, `.tmp`, `.log`, `.webm`, `.mp3`/`.mp4` and the JSONs are
skipped entirely. Non-readable but listed types (`.csv`, `.xml`, `.html`,
`.msg`, `.txt`) still get an entry — so every clickable document has a title
and a download link — but are never sent to the AI.

## `document_reports` entry schema (one per document)

```json
{
  "file": "6.3-Industrial-Consumer-Segment-Google.pdf",
  "title": "Industrial Consumer Segment Google",
  "agenda_item": "6.3",
  "doc_type": "Presentation",
  "ext": "pdf",
  "kind": "PDF document",
  "download_url": "/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS/BOARD/2026-09-14/6.3-Industrial-Consumer-Segment-Google.pdf",
  "executive_summary": "Google's presentation to the ERCOT Board ... asks ERCOT to shift its planning and batch processes from rationing capacity to enabling growth.",
  "sponsor": "Doug Lewin, Eric Schubert, and Chris Matos",
  "company": "Google"
}
```

Plus one meeting-level field on the profile:

```json
"meeting_time": "9:30 AM"
```

**Filename-derived (always, free):**
- `title` — the document title: the stem with separators turned into spaces,
  the agenda prefix removed, and date/version noise stripped.
  **Two traps, both fixed in `clean_title()` and worth keeping fixed:** a month
  abbreviation must be matched with a trailing `\b` and never a greedy
  `[a-z]*` (otherwise `mar` eats "Market", `dec` eats "Decision", `may` eats
  "Mayor"); and a **leading** 4-digit year is part of the title
  ("2027 ERCOT Methodologies…") while a later one is a date stamp.
  "public" and "draft" are title words, not version noise.
- `agenda_item` — the leading `6.3`; ERCOT numbers meeting materials to the
  agenda, so this is the document's place in the meeting.
- `doc_type` — `Agenda` · `Minutes` · `Ballot` · `Segment Representatives` ·
  `Impact Analysis` · `Revision Request` · `Comments` · `Report` · `Update` ·
  `Presentation` · `Notice` · `Charter` · `Workbook` · `Document`.
- `kind` — the file format in words, for the "Document type" field.
- `download_url` — %-encoded path to the original (the download button).

**Read from the document by `--ai` (Claude):**
- `executive_summary` — 2–4 sentences, **at most 120 words**: what the document
  covers, what it asks the committee to do or decide, and the numbers that
  matter. An agenda or a set of minutes covers many items, so it summarizes the
  meeting's shape rather than listing every one.
- `sponsor` — the person who authored or presented it, as named in the document.
  A person, never a committee; `null` rather than a guess from the committee name.
- `company` — the organization that person speaks for.

**Meeting-level, from the calendar log (free):**
- `meeting_time` — the clock time, matched out of
  `ERCOT.STKHDR.MEETS/_calendar_log/<date>.json` on (committee, date). The log
  is a daily scrape that only began in **November 2026**, so a miss is normal
  for the archive and the card falls back to the long-form meeting date.

Use `null` for unknown scalars.

## Steps

1. For each meeting folder: list the documents the group homepage lists, in
   agenda order (same `doc_sort_key` as the manifest).
2. Filename-derive `title` / `agenda_item` / `doc_type` / `kind` /
   `download_url` for every one (fast, full coverage).
3. Carry forward any `executive_summary` / `sponsor` / `company` already earned
   for that filename.
4. With **`--ai`**, for each readable document still lacking an executive
   summary: extract its text, ask Claude for
   `{executive_summary, sponsor, company}`, merge into the entry.
5. Set `document_reports` and `meeting_time`, leave the rest of the profile
   untouched, and skip the write entirely when nothing changed.
6. Report counts, AI calls, tokens and list-equivalent cost.

## Batch / refresh

```
python "Database Codes/download_STKHDR_Meets/gen_stkhdr_doc_summaries.py"
python ... gen_stkhdr_doc_summaries.py BOARD                   # one committee
python ... gen_stkhdr_doc_summaries.py BOARD 2026-09-14 --ai   # one meeting, read the docs
python ... gen_stkhdr_doc_summaries.py --ai --budget 500       # paced backfill
python ... gen_stkhdr_doc_summaries.py BOARD 2026-09-14 --ai --force  # re-read

# what the nightly routine runs:
python ... gen_stkhdr_doc_summaries.py --ai --model haiku --until 2025-12-31 --budget 1000
python ... gen_stkhdr_doc_summaries.py --ai --model opus  --since 2026-01-01 --budget 40
```

| Flag | Effect |
|---|---|
| `--ai` | read the documents; without it only the free filename fields are written |
| `--budget N` | stop after N AI calls (exit 2, resume next run) |
| `--model haiku\|sonnet\|opus` | sets `POWERTALKS_AI_MODEL` for the process, so one run can be Haiku and the next Opus with no file edited |
| `--since` / `--until` | bound the meeting dates (`YYYY-MM-DD`) — how the routine splits eras |
| `--force` | re-read documents that already have a summary |
| *positional* | committee abbreviations and/or exact meeting dates |

Meetings are visited **newest first**, so a budgeted run fills the end anyone
is most likely to open. Resume is **per document**: a meeting is skipped only
when every readable document in it already has a summary, so a budget that runs
out mid-meeting is picked up exactly where it stopped. Exit code 2 means the run
stopped on its budget or an unavailable backend with work still pending — the
same contract the gallery routine uses.

AI runs on the Claude subscription through `summarize_MKT_Rules/ai_backend.py`
(`cli` backend, lean mode). The metered API is never used.

## Measured cost (2026-11-21, Opus in lean mode)

Readable documents in the tree: **32,887**, across 2,386 meetings and 42
committees — 1,638 of them in the current year, 31,249 in the archive.

| | Opus-lean | Haiku-lean |
|---|---|---|
| Measured $/document | **$0.0501** (31 calls) | **$0.00093** (12 calls) |
| Measured s/document | 5.2 s | 3.3 s |
| Whole tree | ~$1,650 · 47 h | ~$31 · 30 h |

Haiku is **54× cheaper per call here**, and the gap is larger than list price
alone implies because Haiku also writes tighter summaries (median 75 words
against Opus's 109) for the same prompt.

Extraction is never the bottleneck: 0.36 s per document averaged over all eight
formats, 3.3 h for the whole tree, zero empty reads in a 48-file sample spanning
`.doc`, `.ppt`, `.xls` and the modern formats.

**The binding constraint is subscription quota, not time.** An executive summary
is a bulk extraction job, not a reasoning job, so the archive runs on Haiku and
the current year — the part anyone actually opens — on Opus. Quality was checked
before committing to that split: on a 2014 WMS meeting Haiku correctly pulled
the $0.01/MWh PTP option bid price, the NPRR numbers endorsed and tabled, and
what each document asked the committee to do.

## Nightly routine

`run_routine.py` runs three steps, in the stakeholder block:

| Step | Command | Cost/night |
|---|---|---|
| `STKHDR meeting document index` | no AI, whole tree | free, ~41 s |
| `BACKFILL meeting documents, archive` | `--model haiku --until <last year>-12-31 --budget` `--meeting-doc-budget` (1000) | ~$0.93, ~55 min |
| `BACKFILL meeting documents, current year` | `--model opus --since <this year>-01-01 --budget` `--meeting-doc-live-budget` (40) | ~$2.00, ~3.5 min |

At those budgets the 31,249-document archive clears in about **31 nights** and
the current year in about **41**. The era boundary is computed from the clock, so
it rolls forward every January on its own.

**The archive pass runs before the current-year pass on purpose.** If an earlier
Opus step has eaten the subscription window, what is left should go to the cheap
pass that clears a thousand documents rather than the expensive one that clears
forty. Both resume per document and neither writes anything for a failed call,
so a spent window costs a night and nothing else — turn
`--meeting-doc-live-budget` down first if that keeps happening.

## How it surfaces (cross-skill)

- The document **list** lives on the group homepage (expand a meeting).
- Clicking a document sets `activeMeetingDoc = {committee, date, file}`. Then
  both panels switch: `MeetingTracksItemHome` renders title / executive summary
  / download, and `MeetingDocProfileCard` renders
  Sponsor / Company / Stakeholder Meeting / Meeting Time.
- See `Set-Meeting-Tracks-Item-Rule-Homepage` for the wiring.

## Common mistakes

| Mistake | Fix |
|---|---|
| Writing separate per-document JSON files | Reports live in `Profile.json["document_reports"]` |
| Rewriting the whole profile | Only set `document_reports` + `meeting_time` |
| Letting `gen_stkhdr_profiles.py --overwrite` drop them | It carries both fields forward; keep that guard |
| Skipping `.ppt`/`.pptx` | They are the largest document class in this tree |
| Summarizing the whole meeting | That is `ERCOT-Stakeholder-Meeting-Profile`; this is one document |
| Greedy month regex in `clean_title` | `mar` + `[a-z]*` eats "Market" — match months with a trailing `\b` |
| Un-encoded `download_url` | %-encode spaces and specials, per path segment |
| Running the whole tree on Opus without a budget | One `--ai` pass over 32,887 documents is ~$1,650 of quota weight |
