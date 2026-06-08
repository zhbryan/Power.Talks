---
name: ERCOT_Market_Rules_Downloader
description: Skill for maintaining and running ERCOT market rules document downloaders. Covers how the scripts work, how to run them, how to configure them, and how to create a new downloader for any market rules category — NPRR, NOGRR, PGRR, RMGRR, SCR, COPMGRR.
trigger: When the user asks about downloading ERCOT market rules documents, running any market rules downloader, updating rule files, or creating a new downloader script for a category.
---

# ERCOT Market Rules Document Downloader

## Overview

Each market rules category has a dedicated downloader script in `Database Codes/download_MKT_Rules/`. All scripts share the same architecture — they scrape ERCOT's website for all statuses of a revision request type, compare against locally saved files, and download only what is new.

| Category | Script | Statuses covered |
|---|---|---|
| NPRR | `download_ercot_nprr.py` | Pending, Withdrawn, Approved |
| NOGRR | `download_ercot_nogrr.py` | Pending, Withdrawn, Approved, Rejected |
| PGRR | `download_ercot_pgrr.py` | Pending, Withdrawn, Approved |
| RMGRR | `download_ercot_rmgrr.py` | Pending, Withdrawn, Approved |
| SCR | `download_ercot_scr.py` | Pending, Withdrawn, Approved, Rejected |
| COPMGRR | `download_ercot_copmgrr.py` | Pending, Withdrawn, Approved |

All downloaded files are saved to:
```
Documents Database/ERCOT.MKT.RULES/<CATEGORY>/
    <ISSUE_ID>/
        <document files>
```

---

## How to Run an Existing Script

```bash
cd "E:\wamp64\www\Power.Talks"
python "Database Codes/download_MKT_Rules/download_ercot_nprr.py"
```

Replace `download_ercot_nprr.py` with the script for the desired category.

**Dependencies** (install once, shared by all scripts):
```bash
pip install requests beautifulsoup4 openpyxl
```

---

## What Each Script Does on a Run

1. Fetches the **pending** list from `ercot.com/mktrules/issues/<slug>` (scrapes the "Pending" section; some scripts fall back to the pending report page if the section is not found).
2. Fetches **withdrawn**, **approved**, and (where applicable) **rejected** lists from the report pages.
3. For each category, compares the full live list against the local Excel tracker — only issues not yet tracked are downloaded.
4. For each new issue:
   - Visits `ercot.com/mktrules/issues/<ISSUE_ID>`.
   - Finds all downloadable file links (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`).
   - Downloads only files not already present on disk — skips everything else.
5. Updates each Excel tracker sheet with the full current list and a timestamp.
6. Prints a final summary: new files per category and total.

---

## SETTINGS Block (common to all scripts)

| Setting | Default | Purpose |
|---|---|---|
| `<CATEGORY>_NUMBERS` | `None` | Override auto-fetch with a specific list, e.g. `[956, 1214]`. Applies to all statuses. |
| `BASE_DIR` | `...ERCOT.MKT.RULES\<CATEGORY>` | Root output folder. All scripts use a single `BASE_DIR` for all statuses. |
| `REQUEST_DELAY` | `1.5` | Seconds to pause between HTTP requests. |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx` | File extensions to download. |
| `EXCEL_TRACKER` | `BASE_DIR\Current List of <CATEGORY>s.xlsx` | Excel file tracking all seen issue numbers. |
| `APPROVED_MIN_<CATEGORY>` | `0` (NPRR: `100`) | Skip approved issues below this number (early issues often have no documents online). |

---

## Key Functions (identical across all scripts)

| Function | Purpose |
|---|---|
| `get_pending_<x>s()` | Scrapes the Pending section of the listing page. Falls back to report page if not found (NOGRR, SCR pattern). |
| `fetch_<x>_numbers_from_report(url, label)` | Generic helper — scrapes any report page and returns sorted issue numbers. |
| `get_document_links(n)` | Visits one issue page and returns all downloadable file links as `[{"label": …, "url": …}]`. |
| `download_file(url, dest_path)` | Streams in 64 KB chunks to a `.tmp` file, then `os.replace()` on success. Returns `True` on success. |
| `process_<x>_list(list, output_dir)` | Check-and-download loop for a full list. Returns `(files_downloaded, issues_updated)`. |
| `load_excel_<x>s(sheet_name)` | Reads tracked issue numbers from one sheet of the Excel tracker. |
| `update_excel_<x>s(sheet_name, list)` | Overwrites a sheet with the full current list + timestamp header. |
| `resolve_new(full_list, sheet_name, label)` | Compares list against tracker; returns only new issues (NOGRR/SCR pattern). |
| `sanitize(name)` | Strips Windows-illegal characters from filenames. |
| `safe_fname(fname, dest_dir)` | Truncates filenames to keep the full path under 240 characters. |

---

## Per-Category URL Reference

| Category | Listing page | Pending report | Withdrawn | Approved | Rejected | Issue page |
|---|---|---|---|---|---|---|
| NPRR | `/mktrules/issues/nprr` | — | `.../reports/nprr/withdrawn` | `.../reports/nprr/approved` | — | `/mktrules/issues/NPRR{n}` |
| NOGRR | `/mktrules/issues/nogrr` | `.../reports/nogrr/pending` | `.../reports/nogrr/withdrawn` | `.../reports/nogrr/approved` | `.../reports/nogrr/rejected` | `/mktrules/issues/NOGRR{n}` |
| PGRR | `/mktrules/issues/pgrr` | `.../reports/pgrr/pending` | `.../reports/pgrr/withdrawn` | `.../reports/pgrr/approved` | — | `/mktrules/issues/PGRR{n}` |
| RMGRR | `/mktrules/issues/rmgrr` | `.../reports/rmgrr/pending` | `.../reports/rmgrr/withdrawn` | `.../reports/rmgrr/approved` | — | `/mktrules/issues/RMGRR{n}` |
| SCR | `/mktrules/issues/scr` | `.../reports/scr/pending` | `.../reports/scr/withdrawn` | `.../reports/scr/approved` | `.../reports/scr/rejected` | `/mktrules/issues/SCR{n}` |
| COPMGRR | `/mktrules/issues/copmgrr` | — | `.../reports/copmgrr/withdrawn` | `.../reports/copmgrr/approved` | — | `/mktrules/issues/COPMGRR{n:03d}` |

All base URLs are relative to `https://www.ercot.com`. Verify the report page URLs are live before creating a new script — not all categories publish all status pages.

---

## Creating a New Script

Use `Database Codes/download_MKT_Rules/download_ercot_nprr.py` as the base template. Apply these substitutions throughout:

| NPRR value | Replace with |
|---|---|
| `NPRR` (all caps, in variable names) | New category abbreviation (e.g. `PGRR`) |
| `nprr` (lowercase, in URLs and strings) | Lowercase abbreviation (e.g. `pgrr`) |
| `"Nodal Protocol Revision Request"` in docstring | Full name of the new category |
| `APPROVED_MIN_NPRR = 100` | Set to `0` unless early issues are known to have no documents |
| `PENDING_DIR = r"...\NPRR"` | Point to `...\<CATEGORY>` |
| `EXCEL_TRACKER = r"...\Current List of NPRRs.xlsx"` | `...\Current List of <CATEGORY>s.xlsx` |
| `re.search(r"/mktrules/issues/NPRR(\d+)")` | `r"/mktrules/issues/<CATEGORY>(\d+)"` |
| `f"NPRR{nprr}"` (folder name) | `f"<CATEGORY>{n}"` |
| `User-Agent: NPRR-Downloader/1.0` | `<CATEGORY>-Downloader/1.0` |

**COPMGRR-specific difference:** COPMGRR uses a zero-padded 3-digit issue number in the URL:
```python
ISSUE_URL = "https://www.ercot.com/mktrules/issues/COPMGRR{n:03d}"
folder_name = f"COPMGRR{copmgrr:03d}"
```
All other categories use plain integers.

**Adding a Rejected status** (pattern from `download_ercot_nogrr.py`):
1. Add `<CATEGORY>_REJECTED_URL = "https://www.ercot.com/mktrules/issues/reports/<slug>/rejected"`
2. In `main()`: call `fetch_<x>_numbers_from_report(REJECTED_URL, "rejected")`, `resolve_new()`, `process_<x>_list()`, `update_excel_<x>s("List_Rejected", ...)`.
3. Add a rejected line to the final summary print block.

---

## Excel Tracker Sheets

All scripts maintain the same sheet structure:

| Sheet | Contents |
|---|---|
| `List_Pending` | All pending issues seen on the most recent run |
| `List_Withdrawn` | All withdrawn issues seen on the most recent run |
| `List_Approved` | All approved issues seen on the most recent run |
| `List_Rejected` | All rejected issues (only where the category has a rejected report page) |

Each sheet has a header row: `[<CATEGORY>_Number, "Last Updated: YYYY-MM-DD HH:MM:SS"]`.

---

## Targeting Specific Issues

To download or refresh specific issue numbers without running the full scrape:

```python
# Example for NPRR — set at the top of the script
NPRR_NUMBERS = [1264, 1282, 1295]
```

All status loops use this list instead of auto-fetching. Useful for backfilling a specific issue or verifying a known issue's documents are complete.

---

## Known Issues and Fixes (applied in all scripts)

| Issue | Fix |
|---|---|
| `FileNotFoundError` on long filenames | `unquote()` + `safe_fname()` keeps paths under 240 chars |
| Corrupt file from interrupted download | `.tmp` → `os.replace()` pattern — partial downloads never linger |
| Pending section not found on listing page | NOGRR/SCR scripts fall back to the pending report page automatically |
| Issue page returns 404 | `get_document_links()` returns `[]` on 404 — issue is skipped silently |
