---
name: NOGRR_Downloader
description: Skill for maintaining and running the ERCOT NOGRR document downloader. Covers how the script works, how to run it, how to configure it, and how to extend or troubleshoot it.
trigger: When the user asks about downloading NOGRR documents, running the NOGRR downloader, updating NOGRR files, or modifying download_ercot_nogrr.py.
---

# ERCOT NOGRR Document Downloader

## Overview

`Database Codes/download_ercot_nogrr.py` automatically scrapes ERCOT's website for **pending**, **withdrawn**, **approved**, and **rejected** Nodal Operating Guide Revision Requests (NOGRRs), compares what is already saved locally, and downloads only new documents (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`).

All downloaded files are saved to:
```
Documents Database/ERCOT.MKT.RULES/NOGRR/
    NOGRR<number>/
        <document files>
```

One sub-folder per NOGRR number. All statuses share the same root folder.

---

## How to Run

```bash
cd "C:\Users\chunl\OneDrive\Documents\Business Ventures\Power.Talks"
python "Database Codes/download_ercot_nogrr.py"
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4 openpyxl
```

---

## What It Does on Each Run

1. Fetches the list of **pending** NOGRRs from `ercot.com/mktrules/issues/nogrr` (scrapes the "Pending" section, falls back to the pending report page).
2. Fetches the list of **withdrawn** NOGRRs from `ercot.com/mktrules/issues/reports/nogrr/withdrawn`.
3. Fetches the list of **approved** NOGRRs from `ercot.com/mktrules/issues/reports/nogrr/approved`.
4. Fetches the list of **rejected** NOGRRs from `ercot.com/mktrules/issues/reports/nogrr/rejected`.
5. For each category, compares the full list against the Excel tracker — only new NOGRRs (not yet in the tracker) are downloaded.
6. For each new NOGRR:
   - Visits `ercot.com/mktrules/issues/NOGRR<number>`.
   - Finds all downloadable file links.
   - Downloads only files not already present locally — skips everything already on disk.
7. Updates each Excel sheet with the full current list.
8. Prints a final summary: new files downloaded per category and total.

---

## SETTINGS Block (top of the script)

| Setting | Default | Purpose |
|---------|---------|---------|
| `NOGRR_NUMBERS` | `None` | Override auto-fetch with a specific list, e.g. `[100, 110]`. Applies to all categories. |
| `BASE_DIR` | `...ERCOT.MKT.RULES\NOGRR` | Root output folder for all NOGRRs. |
| `REQUEST_DELAY` | `1.5` | Seconds to pause between HTTP requests. |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx` | File extensions to download. |
| `EXCEL_TRACKER` | `BASE_DIR\Current List of NOGRRs.xlsx` | Excel file for tracking seen NOGRR numbers. |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `get_pending_nogrrs()` | Scrapes the Pending section of the NOGRR listing page. Falls back to report page if not found. |
| `fetch_nogrr_numbers_from_report(url, label)` | Generic helper — scrapes any NOGRR report page and returns sorted numbers. |
| `get_document_links(nogrr)` | Visits one NOGRR's issue page and returns all downloadable file links. |
| `download_file(url, dest_path)` | Downloads a single file. Streams in 64 KB chunks with tmp-file safety. |
| `process_nogrr_list(nogrr_list, output_dir)` | Runs the check-and-download loop for a full list. Returns `(files_downloaded, nogrrs_updated)`. |
| `load_excel_nogrrs(sheet_name)` | Reads tracked NOGRR numbers from a sheet in the Excel tracker. |
| `update_excel_nogrrs(sheet_name, nogrr_list)` | Overwrites a sheet with the full current list + timestamp header. |
| `resolve_new(full_list, sheet_name, label)` | Compares full list against Excel tracker; returns only new NOGRRs. |
| `sanitize(name)` | Strips Windows-illegal characters from filenames. |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters. |

---

## Excel Tracker Sheets

| Sheet | Contents |
|-------|---------|
| `List_Pending` | All pending NOGRRs seen on the most recent run |
| `List_Withdrawn` | All withdrawn NOGRRs seen on the most recent run |
| `List_Approved` | All approved NOGRRs seen on the most recent run |
| `List_Rejected` | All rejected NOGRRs seen on the most recent run |

---

## ERCOT Source URLs

| Category | URL |
|----------|-----|
| Pending list | `https://www.ercot.com/mktrules/issues/nogrr` |
| Pending report | `https://www.ercot.com/mktrules/issues/reports/nogrr/pending` |
| Withdrawn list | `https://www.ercot.com/mktrules/issues/reports/nogrr/withdrawn` |
| Approved list | `https://www.ercot.com/mktrules/issues/reports/nogrr/approved` |
| Rejected list | `https://www.ercot.com/mktrules/issues/reports/nogrr/rejected` |
| Individual NOGRR | `https://www.ercot.com/mktrules/issues/NOGRR{n}` |

---

## Known Issues & Fixes Applied

| Issue | Fix |
|-------|-----|
| `FileNotFoundError` on long filenames | `unquote()` + `safe_fname()` truncation keeps paths under 260 chars. |
| Interrupted download leaves corrupt file | Writes to `.tmp` first, then `os.replace()` on success — corrupt files never linger. |

---

## Extending the Script

**Add a new NOGRR status category:**
1. Add a URL constant: `NOGRR_<STATUS>_URL = "https://www.ercot.com/mktrules/issues/reports/nogrr/<status>"`
2. In `main()`: call `fetch_nogrr_numbers_from_report(NOGRR_<STATUS>_URL, "<status>")`, then `resolve_new()`, `process_nogrr_list()`, and `update_excel_nogrrs()`.
3. Add a line to the final summary print block.

**Target specific NOGRRs only:**
```python
NOGRR_NUMBERS = [100, 110, 120]
```
Set this at the top of the script. All category loops will use this list instead of auto-fetching.
