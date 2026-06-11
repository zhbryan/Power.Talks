---
name: SCR_Downloader
description: Skill for maintaining and running the ERCOT SCR document downloader. Covers how the script works, how to run it, how to configure it, and how to extend or troubleshoot it.
trigger: When the user asks about downloading SCR documents, running the SCR downloader, updating SCR files, or modifying download_ercot_scr.py.
---

# ERCOT SCR Document Downloader

## Overview

`Database Codes/download_ercot_scr.py` automatically scrapes ERCOT's website for **pending**, **withdrawn**, **approved**, and **rejected** System Change Requests (SCRs), compares what is already saved locally, and downloads only new documents (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`).

All downloaded files are saved to:
```
Documents Database/ERCOT.MKT.RULES/SCR/
    SCR<number>/
        <document files>
```

One sub-folder per SCR number. All statuses share the same root folder.

---

## How to Run

```bash
cd "C:\Users\chunl\OneDrive\Documents\Business Ventures\Power.Talks"
python "Database Codes/download_ercot_scr.py"
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4 openpyxl
```

---

## What It Does on Each Run

1. Fetches the list of **pending** SCRs from `ercot.com/mktrules/issues/scr` (scrapes the "Pending" section, falls back to the pending report page).
2. Fetches the list of **withdrawn** SCRs from `ercot.com/mktrules/issues/reports/scr/withdrawn`.
3. Fetches the list of **approved** SCRs from `ercot.com/mktrules/issues/reports/scr/approved`.
4. Fetches the list of **rejected** SCRs from `ercot.com/mktrules/issues/reports/scr/rejected`.
5. For each category, compares the full list against the Excel tracker — only new SCRs (not yet in the tracker) are downloaded.
6. For each new SCR:
   - Visits `ercot.com/mktrules/issues/SCR<number>`.
   - Finds all downloadable file links.
   - Downloads only files not already present locally — skips everything already on disk.
7. Updates each Excel sheet with the full current list.
8. Prints a final summary: new files downloaded per category and total.

---

## SETTINGS Block (top of the script)

| Setting | Default | Purpose |
|---------|---------|---------|
| `SCR_NUMBERS` | `None` | Override auto-fetch with a specific list, e.g. `[800, 820]`. Applies to all categories. |
| `BASE_DIR` | `...ERCOT.MKT.RULES\SCR` | Root output folder for all SCRs. |
| `REQUEST_DELAY` | `1.5` | Seconds to pause between HTTP requests. |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx` | File extensions to download. |
| `EXCEL_TRACKER` | `BASE_DIR\Current List of SCRs.xlsx` | Excel file for tracking seen SCR numbers. |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `get_pending_scrs()` | Scrapes the Pending section of the SCR listing page. Falls back to report page if not found. |
| `fetch_scr_numbers_from_report(url, label)` | Generic helper — scrapes any SCR report page and returns sorted numbers. |
| `get_document_links(scr)` | Visits one SCR's issue page and returns all downloadable file links. |
| `download_file(url, dest_path)` | Downloads a single file. Streams in 64 KB chunks with tmp-file safety. |
| `process_scr_list(scr_list, output_dir)` | Runs the check-and-download loop for a full list. Returns `(files_downloaded, scrs_updated)`. |
| `load_excel_scrs(sheet_name)` | Reads tracked SCR numbers from a sheet in the Excel tracker. |
| `update_excel_scrs(sheet_name, scr_list)` | Overwrites a sheet with the full current list + timestamp header. |
| `resolve_new(full_list, sheet_name, label)` | Compares full list against Excel tracker; returns only new SCRs. |
| `sanitize(name)` | Strips Windows-illegal characters from filenames. |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters. |

---

## Excel Tracker Sheets

| Sheet | Contents |
|-------|---------|
| `List_Pending` | All pending SCRs seen on the most recent run |
| `List_Withdrawn` | All withdrawn SCRs seen on the most recent run |
| `List_Approved` | All approved SCRs seen on the most recent run |
| `List_Rejected` | All rejected SCRs seen on the most recent run |

---

## ERCOT Source URLs

| Category | URL |
|----------|-----|
| Pending list | `https://www.ercot.com/mktrules/issues/scr` |
| Pending report | `https://www.ercot.com/mktrules/issues/reports/scr/pending` |
| Withdrawn list | `https://www.ercot.com/mktrules/issues/reports/scr/withdrawn` |
| Approved list | `https://www.ercot.com/mktrules/issues/reports/scr/approved` |
| Rejected list | `https://www.ercot.com/mktrules/issues/reports/scr/rejected` |
| Individual SCR | `https://www.ercot.com/mktrules/issues/SCR{n}` |

---

## Known Issues & Fixes Applied

| Issue | Fix |
|-------|-----|
| `FileNotFoundError` on long filenames | `unquote()` + `safe_fname()` truncation keeps paths under 260 chars. |
| Interrupted download leaves corrupt file | Writes to `.tmp` first, then `os.replace()` on success — corrupt files never linger. |

---

## Extending the Script

**Add a new SCR status category:**
1. Add a URL constant: `SCR_<STATUS>_URL = "https://www.ercot.com/mktrules/issues/reports/scr/<status>"`
2. In `main()`: call `fetch_scr_numbers_from_report(SCR_<STATUS>_URL, "<status>")`, then `resolve_new()`, `process_scr_list()`, and `update_excel_scrs()`.
3. Add a line to the final summary print block.

**Target specific SCRs only:**
```python
SCR_NUMBERS = [800, 820, 830]
```
Set this at the top of the script. All category loops will use this list instead of auto-fetching.
