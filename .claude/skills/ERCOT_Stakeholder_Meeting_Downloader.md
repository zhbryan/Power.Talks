---
name: ERCOT_Stakeholder_Meeting_Downloader
description: Skill for maintaining and running ERCOT stakeholder committee meeting document downloaders. Covers how the scripts work, how to run them, how to configure them, and how to create a new downloader for any active committee.
trigger: When the user asks about downloading ERCOT stakeholder meeting documents, running a committee downloader, updating meeting files, or creating a new downloader for a committee.
---

# ERCOT Stakeholder Meeting Document Downloader

## Overview

All committee downloader scripts live in `Database Codes/download_STKHDR_Meets/`. Each script follows the same architecture: scrapes the committee's year pages on `ercot.com/committees`, collects calendar page URLs for each meeting, fetches each calendar page for downloadable documents, and saves them locally — skipping any files already present.

All downloaded files are saved to:
```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/
    YYYY-MM-DD/
        <document files>
```

One sub-folder per meeting date. Files are never overwritten — only new files are added.

---

## How to Run (ROS example)

```bash
cd "E:\wamp64\www\Power.Talks"
python "Database Codes/download_STKHDR_Meets/download_ercot_ros.py"
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4
```

---

## What It Does on Each Run

1. For each year in `YEAR_START` … `YEAR_END` (inclusive):
   - Fetches `ercot.com/committees/<path>/YEAR` (or the main page for the current year).
   - Scrapes all calendar links matching the committee's URL slug pattern.
   - Skips links marked as cancelled in the surrounding page text.
2. For each non-cancelled meeting calendar URL:
   - Fetches `ercot.com/calendar/MMDDYYYY-<SLUG>`.
   - Extracts all `<a href>` links whose extension is in `DOWNLOAD_EXTS`.
3. For each document URL found:
   - Derives the target path: `BASE_DIR/YYYY-MM-DD/<filename>`.
   - Skips if the file already exists.
   - Downloads via streaming (64 KB chunks), writing to a `.tmp` file first, then renaming on success.
4. Prints a final summary: Downloaded | Skipped | Errors.

---

## SETTINGS Block

| Setting | Default (ROS) | Purpose |
|---------|---------------|---------|
| `YEAR_START` | `2010` | First year to fetch |
| `YEAR_END` | `date.today().year` | Last year to fetch (inclusive) |
| `MEETING_DATES` | `None` | Override: list of ISO dates to process, e.g. `["2025-01-09"]`. Fetches only those meetings. |
| `BASE_DIR` | `...ERCOT.STKHDR.MEETS\ROS` | Root folder; files saved to `BASE_DIR/YYYY-MM-DD/` |
| `REQUEST_DELAY` | `1.0` | Seconds between HTTP requests |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx .pptx .ppt .zip` | Extensions to download |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `year_page_url(year)` | Returns the correct ERCOT URL for the given year (main page for current year, `/YEAR` path for past years) |
| `get_meeting_urls(year)` | Fetches one year page, scrapes `<a href>` for calendar links matching the committee slug, skips cancelled entries, returns `[(date_iso, url)]` |
| `get_document_links(calendar_url)` | Fetches one calendar page, returns all downloadable document URLs |
| `download_file(url, dest_path)` | Downloads a single file with `.tmp` safety. Returns `'ok'`, `'skip'`, or `'err'` |
| `process_meetings(meetings)` | Iterates meeting list, calls `get_document_links` + `download_file` for each. Returns `(ok, skip, err)` |
| `sanitize(name)` | Strips Windows-illegal characters from filenames |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters |

---

## Creating a Downloader for Another Committee

Use `Database Codes/download_STKHDR_Meets/download_ercot_ros.py` as the template. Apply these substitutions:

| ROS value | Replace with |
|-----------|-------------|
| `"ROS"` in docstring and print labels | Committee abbreviation (e.g. `"TAC"`) |
| `BASE_DIR = r"...\ROS"` | `r"...\<COMMITTEE_ABBREV>"` |
| `ROS_BASE_URL = "https://www.ercot.com/committees/ros"` | Committee URL from table below |
| `re.search(r"/calendar/(\d{8})-ROS", href, re.IGNORECASE)` | Replace `-ROS` with the committee's calendar slug prefix (see table below) |
| `2010` in `YEAR_START` | First year with data (see table below) |

The `download_file`, `sanitize`, `safe_fname`, `get_document_links`, and `process_meetings` functions are identical — copy them verbatim.

---

## Committee URL and Slug Reference

For the full in-scope committee list see `ERCOT_Stakeholder_Meetings_Links.md`. Key values needed when creating a new downloader:

### Board and sub-committees

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | `YEAR_START` |
|--------|---------------|---------------------|--------------|
| `Board` | `.../committees/board` | `-Board-of-Directors-Meeting` | `2002` |
| `FA` | `.../committees/board/finance_audit` | `-Finance-_-Audit-Committee` | `2004` |
| `HRG` | `.../committees/board/hr_governance` | `-HR-_-Governance-Committee` | `2002` |
| `TS` | `.../committees/board/tech-security` | `-Technology-_-Security-Committee` | `2023` |

### TAC and sub-groups

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | `YEAR_START` |
|--------|---------------|---------------------|--------------|
| `TAC` | `.../committees/tac` | `-TAC-Meeting\|Special-TAC-Meeting` | `2002` |
| `LLWG` | `.../committees/tac/llwg` | `-LLWG-Meeting` | `2025` |
| `CFSG` | `.../committees/tac/cfsg` | `-CFSG-Meeting` | `2023` |
| `RTCBTF` | `.../committees/inactive/rtcbtf` | `-RTCBTF-Meeting` | `2023` |

### Subcommittees

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | `YEAR_START` |
|--------|---------------|---------------------|--------------|
| `PRS` | `.../committees/prs` | `-PRS-Meeting` | `2010` |
| `RMS` | `.../committees/rms` | `-RMS-Meeting` | `2010` |
| `TDTMS` | `.../committees/rms/tdtms` | `-TDTMS-Meeting` | `2015` |
| `RMTTF` | `.../committees/rms/rmttf` | `-RMTTF-Meeting` | `2015` |
| `ROS` | `.../committees/ros` | `-ROS-Meeting` | `2010` |
| `WMS` | `.../committees/wms` | `-WMS-Meeting` | `2010` |

### ROS working groups

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | `YEAR_START` |
|--------|---------------|---------------------|--------------|
| `IBRWG` | `.../committees/ros/ibrwg` | `-IBRWG-Meeting` | `2023` |
| `BSWG` | `.../committees/ros/bswg` | `-BSWG-Meeting` | `2002` |
| `DWG` | `.../committees/ros/dwg` | `-DWG-Meeting` | `2003` |
| `MWG` | `.../committees/ros/mwg` | `-MWG-Meeting` | `2002` |
| `NDSWG` | `.../committees/ros/ndswg` | `-NDSWG-Meeting` | `2002` |
| `OWG` | `.../committees/ros/owg` | `-OWG-Meeting` | verify |
| `OTWG` | `.../committees/ros/otwg` | `-OTWG-Meeting` | verify |
| `PDCWG` | `.../committees/ros/pdcwg` | `-PDCWG-Meeting` | verify |
| `PLWG` | `.../committees/ros/plwg` | `-PLWG-Meeting` | `2010` |
| `SPWG` | `.../committees/ros/spwg` | `-SPWG-Meeting` | verify |
| `SSWG` | `.../committees/ros/sswg` | `-SSWG-Meeting` | verify |
| `VPWG` | `.../committees/ros/vpwg` | `-VPWG-Meeting` | verify |

### WMS working groups

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | `YEAR_START` |
|--------|---------------|---------------------|--------------|
| `CMWG` | `.../committees/wms/cmwg` | `-CMWG-Meeting` | `2010` |
| `DSWG` | `.../committees/wms/dswg` | `-DSWG-Meeting` | `2002` |
| `SAWG` | `.../committees/wms/sawg` | `-SAWG-Meeting` | `2015` |
| `WMWG` | `.../committees/wms/wmwg` | `-WMWG-Meeting` | `2019` |

### Inactive predecessor

| Abbrev | `ROS_BASE_URL` | Calendar slug regex | Notes |
|--------|---------------|---------------------|-------|
| `IBRTF` | `.../committees/inactive/ibrtf` | `-IBRTF-Meeting` | 2022 only; no `/YEAR` sub-pages — fetch main page directly |

> **All base URLs** are relative to `https://www.ercot.com`. The slug regex is matched against the `href` attribute of `<a>` tags on the year page. All committees also use a `-_-Webex` suffix for virtual meetings — the regex needs only match the committee portion; the Webex suffix is optional and irrelevant for URL collection.

---

## Targeted Run — Specific Dates Only

To re-download or backfill specific meetings without running the full year loop:

```python
MEETING_DATES = ["2025-01-09", "2025-03-06", "2025-05-01"]
```

Set this in the SETTINGS block. The script will fetch only the year pages needed to discover those calendar URLs, then download only those meetings.

---

## Known Issues and Fixes

| Issue | Fix |
|-------|-----|
| `FileNotFoundError` on long filenames | `unquote()` + `safe_fname()` keeps paths under 240 chars |
| Corrupt file from interrupted download | `.tmp` → `os.replace()` pattern — partial files never remain |
| ERCOT returns the committee main page instead of the year sub-page | Year pages are only served when the year exists; for the current year always use the main page URL (no `/YEAR` suffix) |
| Calendar page returns no document links | ERCOT may have not yet posted materials; re-run after the meeting date |
| `CANCELLED` detection misses edge cases | The cancelled check looks at `a.parent` text — if ERCOT changes page structure, widen the search to `a.parent.parent` |
