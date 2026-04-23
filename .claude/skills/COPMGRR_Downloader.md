---
name: COPMGRR_Downloader
description: Skill for maintaining and running the ERCOT COPMGRR document downloader. Covers how the script works, how to run it, how to configure it, and how to extend or troubleshoot it.
trigger: When the user asks about downloading COPMGRR documents, running the COPMGRR downloader, updating COPMGRR files, or modifying download_ercot_copmgrr.py.
---

# ERCOT COPMGRR Document Downloader

## Overview

`Database Codes/download_ercot_copmgrr.py` automatically scrapes ERCOT's website for **pending**, **withdrawn**, and **approved** Congestion Offset Payment Mechanism Guide Revision Requests (COPMGRRs), compares what is already saved locally, and downloads only new documents (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`).

All downloaded files are saved to:
```
Documents Database/ERCOT.MKT.RULES/COPMGRR/
    COPMGRR<number>/
        <document files>
```

One sub-folder per COPMGRR number. All statuses share the same root folder.

---

## How to Run

```bash
cd "E:\wamp64\www\Power.Talks"
python "Database Codes/download_ercot_copmgrr.py"
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4 openpyxl
```

---

## What It Does on Each Run

1. Fetches the list of **pending** COPMGRRs from `ercot.com/mktrules/issues/copmgrr` (scrapes the "Pending" section).
2. Fetches the list of **withdrawn** COPMGRRs from `ercot.com/mktrules/issues/reports/copmgrr/withdrawn`.
3. Fetches the list of **approved** COPMGRRs from `ercot.com/mktrules/issues/reports/copmgrr/approved`.
4. For each category, compares the full list against the Excel tracker — only new COPMGRRs (not yet in the tracker) are downloaded.
5. For each new COPMGRR:
   - Visits `ercot.com/mktrules/issues/COPMGRR<number>`.
   - Finds all downloadable file links.
   - Downloads only files not already present locally — skips everything already on disk.
6. Updates each Excel sheet with the full current list.
7. Prints a final summary: new files downloaded per category and total.

---

## SETTINGS Block (top of the script)

| Setting | Default | Purpose |
|---------|---------|---------|
| `COPMGRR_NUMBERS` | `None` | Override auto-fetch with a specific list, e.g. `[10, 15]`. Applies to all categories. |
| `APPROVED_MIN_COPMGRR` | `0` | Only process approved COPMGRRs with a number greater than this value. Set higher if early numbers have no documents. |
| `PENDING_DIR` | `...ERCOT.MKT.RULES\COPMGRR` | Root output folder for pending COPMGRRs. |
| `WITHDRAWN_DIR` | same as `PENDING_DIR` | Root output folder for withdrawn COPMGRRs. |
| `APPROVED_DIR` | same as `PENDING_DIR` | Root output folder for approved COPMGRRs. |
| `REQUEST_DELAY` | `1.5` | Seconds to pause between HTTP requests. |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx` | File extensions to download. |
| `EXCEL_TRACKER` | `PENDING_DIR\Current List of COPMGRRs.xlsx` | Excel file for tracking seen COPMGRR numbers. |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `get_pending_copmgrrs()` | Scrapes the Pending section of the COPMGRR listing page and returns COPMGRR numbers. |
| `get_withdrawn_copmgrrs()` | Scrapes the withdrawn report page and returns a sorted list of numbers. |
| `get_approved_copmgrrs()` | Scrapes the approved report page and returns a sorted list of numbers. |
| `get_document_links(copmgrr)` | Visits one COPMGRR's issue page and returns all downloadable file links. |
| `download_file(url, dest_path)` | Downloads a single file. Streams in 64 KB chunks with tmp-file safety. |
| `process_copmgrr_list(copmgrr_list, output_dir)` | Runs the check-and-download loop for a full list. Returns `(files_downloaded, copmgrrs_updated)`. |
| `load_excel_copmgrrs(sheet_name)` | Reads tracked COPMGRR numbers from a sheet in the Excel tracker. |
| `update_excel_copmgrrs(sheet_name, copmgrr_list)` | Overwrites a sheet with the full current list + timestamp header. |
| `sanitize(name)` | Strips Windows-illegal characters from filenames. |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters. |

---

## Excel Tracker Sheets

| Sheet | Contents |
|-------|---------|
| `List_Pending` | All pending COPMGRRs seen on the most recent run |
| `List_Withdrawn` | All withdrawn COPMGRRs seen on the most recent run |
| `List_Approved` | All approved COPMGRRs seen on the most recent run |

---

## ERCOT Source URLs

| Category | URL |
|----------|-----|
| Pending list | `https://www.ercot.com/mktrules/issues/copmgrr` |
| Withdrawn list | `https://www.ercot.com/mktrules/issues/reports/copmgrr/withdrawn` |
| Approved list | `https://www.ercot.com/mktrules/issues/reports/copmgrr/approved` |
| Individual COPMGRR | `https://www.ercot.com/mktrules/issues/COPMGRR{n}` |

---

## Script Structure

Base the script on `download_ercot_nprr.py` with these substitutions:

| NPRR script | COPMGRR script |
|-------------|----------------|
| `NPRR_NUMBERS` | `COPMGRR_NUMBERS` |
| `APPROVED_MIN_NPRR` | `APPROVED_MIN_COPMGRR` |
| `NPRR_LIST_URL` | `COPMGRR_LIST_URL` |
| `NPRR_WITHDRAWN_URL` | `COPMGRR_WITHDRAWN_URL` |
| `NPRR_APPROVED_URL` | `COPMGRR_APPROVED_URL` |
| `ISSUE_URL = "…/NPRR{n}"` | `ISSUE_URL = "…/COPMGRR{n}"` |
| `EXCEL_TRACKER = "…\Current List of NPRRs.xlsx"` | `EXCEL_TRACKER = "…\Current List of COPMGRRs.xlsx"` |
| `re.search(r"/mktrules/issues/NPRR(\d+)")` | `re.search(r"/mktrules/issues/COPMGRR(\d+)")` |
| Folder prefix `NPRR{n}` | Folder prefix `COPMGRR{n}` |
| `User-Agent: NPRR-Downloader/1.0` | `User-Agent: COPMGRR-Downloader/1.0` |

The `download_file`, `sanitize`, and `safe_fname` functions are identical — copy them verbatim.

---

## Known Issues & Fixes Applied

| Issue | Fix |
|-------|-----|
| `FileNotFoundError` on long filenames | `unquote()` + `safe_fname()` truncation keeps paths under 260 chars. |
| Interrupted download leaves corrupt file | Writes to `.tmp` first, then `os.replace()` on success — corrupt files never linger. |

---

## Extending the Script

**Add a new COPMGRR status category:**
1. Add a URL constant: `COPMGRR_<STATUS>_URL = "https://www.ercot.com/mktrules/issues/reports/copmgrr/<status>"`
2. In `main()`: call the appropriate fetch function, then `load_excel_copmgrrs()`, `process_copmgrr_list()`, and `update_excel_copmgrrs()`.
3. Add a line to the final summary print block.

**Target specific COPMGRRs only:**
```python
COPMGRR_NUMBERS = [10, 15, 20]
```
Set this at the top of the script. All category loops will use this list instead of auto-fetching.
