---
name: NPRR_Downloader
description: Skill for maintaining and running the ERCOT NPRR document downloader. Covers how the script works, how to run it, how to configure it, and how to extend or troubleshoot it.
trigger: When the user asks about downloading NPRR documents, running the NPRR downloader, updating NPRR files, or modifying download_ercot_nprr.py.
---

# ERCOT NPRR Document Downloader

## Overview

`Database Codes/download_ercot_nprr.py` automatically scrapes ERCOT's website for **pending**, **withdrawn**, and **approved** Nodal Protocol Revision Requests (NPRRs), compares what is already saved locally, and downloads only new documents (`.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`).

All downloaded files are saved to:
```
Documents Database/ERCOT.MKT.RULES/NPRR/
    NPRR<number>/
        <document files>
```

One sub-folder per NPRR number. Pending, withdrawn, and approved NPRRs all share the same root folder.

---

## How to Run

```bash
cd "C:\Users\chunl\OneDrive\Documents\Business Ventures\Power.Talks"
python "Database Codes/download_ercot_nprr.py"
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4
```

---

## What It Does on Each Run

1. Fetches the list of **pending** NPRRs from `ercot.com/mktrules/issues/nprr` (scrapes the "Pending" section).
2. Fetches the list of **withdrawn** NPRRs from `ercot.com/mktrules/issues/reports/nprr/withdrawn`.
3. Fetches the list of **approved** NPRRs from `ercot.com/mktrules/issues/reports/nprr/approved`.
4. For each NPRR in all three lists:
   - Visits `ercot.com/mktrules/issues/NPRR<number>`.
   - Finds all downloadable file links (Key Documents section).
   - Compares against the local `NPRR<number>/` folder.
   - Downloads only files not already present — skips everything already on disk.
5. Prints a final summary: new files downloaded per category and total.

---

## SETTINGS Block (top of the script)

| Setting | Default | Purpose |
|---------|---------|---------|
| `NPRR_NUMBERS` | `None` | Override auto-fetch with a specific list, e.g. `[956, 1214]`. Applies to all three categories. |
| `PENDING_DIR` | `...ERCOT.MKT.RULES\NPRR` | Output folder for pending NPRRs. |
| `WITHDRAWN_DIR` | `= PENDING_DIR` | Output folder for withdrawn NPRRs (same as pending). |
| `APPROVED_DIR` | `= PENDING_DIR` | Output folder for approved NPRRs (same as pending). |
| `REQUEST_DELAY` | `1.5` | Seconds to pause between HTTP requests. |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx` | File extensions to download. |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `get_pending_nprrs()` | Scrapes the Pending section of the NPRR listing page. Returns ordered list of NPRR numbers. |
| `get_withdrawn_nprrs()` | Scrapes the withdrawn report page. Returns sorted list. |
| `get_approved_nprrs()` | Scrapes the approved report page. Returns sorted list. |
| `get_document_links(nprr)` | Visits one NPRR's issue page and returns all downloadable file links. |
| `download_file(url, dest_path)` | Downloads a single file. Streams in 64 KB chunks. |
| `process_nprr_list(nprr_list, output_dir)` | Runs the check-and-download loop for a full list. Returns `(files_downloaded, nprrs_updated)`. |
| `sanitize(name)` | Strips Windows-illegal characters from filenames. |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters (Windows path limit). |

---

## ERCOT Source URLs

| Category | URL |
|----------|-----|
| Pending list | `https://www.ercot.com/mktrules/issues/nprr` |
| Withdrawn list | `https://www.ercot.com/mktrules/issues/reports/nprr/withdrawn` |
| Approved list | `https://www.ercot.com/mktrules/issues/reports/nprr/approved` |
| Individual NPRR | `https://www.ercot.com/mktrules/issues/NPRR{n}` |

---

## Known Issues & Fixes Applied

| Issue | Fix |
|-------|-----|
| `UnicodeEncodeError` on Windows console | Replaced `→` and `–` Unicode characters in print statements with ASCII `->` and `-`. |
| `FileNotFoundError` on long filenames | ERCOT URLs use `%20`-encoded spaces; filenames were stored raw, pushing paths over 260 chars. Fixed by calling `unquote()` on the filename before saving, and `safe_fname()` to truncate if still too long. |
| OneDrive permission errors when deleting empty folders | Used `powershell Remove-Item -Recurse -Force` instead of `os.rmdir` / `shutil.rmtree`. |

---

## Extending the Script

**Add a new NPRR status category** (e.g. rejected):
1. Add a URL constant: `NPRR_REJECTED_URL = "https://www.ercot.com/mktrules/issues/reports/nprr/rejected"`
2. Add a dir constant: `REJECTED_DIR = PENDING_DIR`
3. Copy `get_withdrawn_nprrs()` → `get_rejected_nprrs()`, point it at the new URL.
4. In `main()`, call `get_rejected_nprrs()`, run `process_nprr_list(rejected_list, REJECTED_DIR)`, and add a line to the summary.

**Target specific NPRRs only:**
```python
NPRR_NUMBERS = [956, 1214, 1264]
```
Set this at the top of the script. All three category loops will use this list instead of auto-fetching.

**Change output location:**
Update `PENDING_DIR` (and optionally point `WITHDRAWN_DIR` / `APPROVED_DIR` to separate paths if you want them separated).
