---
name: ERCOT_Stakeholder_Meeting_Downloader
description: Skill for maintaining and running the ERCOT stakeholder committee meeting document downloader. Covers how the script works, how to run it, how to configure it, and how to add a new committee to the registry.
trigger: When the user asks about downloading ERCOT stakeholder meeting documents, running a committee downloader, updating meeting files, or adding a new committee to the downloader.
---

# ERCOT Stakeholder Meeting Document Downloader

## Overview

`Database Codes/download_STKHDR_Meets/download_ercot_stkhdr.py` is a single unified script that downloads meeting documents for all (or selected) ERCOT stakeholder committees. It scrapes the committee's year pages on `ercot.com/committees`, collects calendar page URLs for each non-cancelled meeting, fetches each calendar page for downloadable documents, and saves them locally — skipping any files already present.

All downloaded files are saved to:
```
Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/
    YYYY-MM-DD/
        <document files>
```

One sub-folder per meeting date. Files are never overwritten — only new files are added.

The script covers 31 committees across four groups:

| Group | Committees |
|-------|-----------|
| Board | BOARD, FA, HRG, TS |
| TAC | TAC, LLWG, CFSG, RTCBTF |
| Subcommittees | PRS, RMS, TDTMS, RMTTF, ROS, WMS |
| ROS working groups | BSWG, DWG, IBRWG, MWG, NDSWG, OWG, OTWG, PDCWG, PLWG, SPWG, SSWG, VPWG |
| WMS working groups | CMWG, DSWG, SAWG, WMWG |
| Inactive | IBRTF |

---

## How to Run

**Run all committees:**
```bash
cd "E:\wamp64\www\Power.Talks"
python "Database Codes/download_STKHDR_Meets/download_ercot_stkhdr.py"
```

**Run specific committees** — set `COMMITTEES_TO_RUN` in the SETTINGS block:
```python
COMMITTEES_TO_RUN = ["TAC", "WMS", "PRS"]
```

**Dependencies** (install once):
```bash
pip install requests beautifulsoup4
```

---

## What It Does on Each Run

1. Iterates through each committee in `COMMITTEES_TO_RUN` (or all if `None`).
2. For each year in `year_start` … `YEAR_END` (inclusive):
   - Fetches `ercot.com/committees/<path>/YEAR` (or the main page for the current year).
   - Scrapes all `<a href>` links that contain `/calendar/` and match the committee's `slug` regex.
   - Skips links marked as cancelled in the surrounding page text.
3. For each non-cancelled meeting calendar URL:
   - Fetches `ercot.com/calendar/MMDDYYYY-<SLUG>`.
   - Extracts all `<a href>` links whose extension is in `DOWNLOAD_EXTS`.
4. For each document URL found:
   - Derives the target path: `BASE_ROOT/<COMMITTEE>/YYYY-MM-DD/<filename>`.
   - Skips if the file already exists.
   - Downloads via streaming (64 KB chunks), writing to a `.tmp` file first, then renaming on success.
5. Prints a per-committee and grand total summary: Downloaded | Skipped | Errors.

---

## SETTINGS Block

| Setting | Default | Purpose |
|---------|---------|---------|
| `COMMITTEES_TO_RUN` | `None` | `None` = all; or list like `["TAC", "WMS"]` to run a subset |
| `YEAR_END` | `date.today().year` | Last year to fetch (inclusive); each committee defines its own `year_start` |
| `MEETING_DATES` | `None` | Override: list of ISO dates to process, e.g. `["2025-01-09"]` |
| `BASE_ROOT` | `...ERCOT.STKHDR.MEETS` | Root folder; each committee gets `BASE_ROOT/<ABBREV>/YYYY-MM-DD/` |
| `REQUEST_DELAY` | `1.0` | Seconds between HTTP requests |
| `DOWNLOAD_EXTS` | `.pdf .doc .docx .xls .xlsx .pptx .ppt .zip` | Extensions to download |

---

## Key Functions

| Function | Purpose |
|----------|---------|
| `year_page_url(year, base_url, no_year_pages)` | Returns the correct ERCOT URL for the given year (main page for current year or `no_year_pages=True`, `/YEAR` path for past years) |
| `get_meeting_urls(year, cfg)` | Fetches one year page, scrapes `<a href>` for calendar links matching the committee's `slug` regex, skips cancelled entries, returns `[(date_iso, url)]` |
| `get_document_links(calendar_url)` | Fetches one calendar page, returns all downloadable document URLs |
| `download_file(url, dest_path)` | Downloads a single file with `.tmp` safety. Returns `'ok'`, `'skip'`, or `'err'` |
| `process_meetings(meetings, base_dir)` | Iterates meeting list, calls `get_document_links` + `download_file` for each. Returns `(ok, skip, err)` |
| `run_committee(abbrev, cfg)` | Full year-loop + meeting-download sequence for one committee |
| `sanitize(name)` | Strips Windows-illegal characters from filenames |
| `safe_fname(fname, dest_dir)` | Truncates filenames so the full path stays under 240 characters |

---

## Adding a New Committee

Add one entry to the `COMMITTEES` dict at the top of the script:

```python
"ABBREV": {
    "url": "https://www.ercot.com/committees/<path>",
    "slug": r"-ABBREV-Meeting",
    "year_start": YYYY,
    # "no_year_pages": True,  # only for committees with no /YEAR sub-pages
},
```

Then create the corresponding folder under `Documents Database/ERCOT.STKHDR.MEETS/ABBREV/` (the script will create `YYYY-MM-DD` sub-folders automatically).

---

## Committee URL and Slug Reference

For the full in-scope committee list see `ERCOT_Stakeholder_Meetings_Links.md`. Key values for adding new entries:

### Board and sub-committees

| Abbrev | URL path | Slug regex | `year_start` |
|--------|----------|------------|--------------|
| `BOARD` | `/committees/board` | `-Board-of-Directors-Meeting` | `2002` |
| `FA` | `/committees/board/finance_audit` | `-Finance-_-Audit-Committee` | `2004` |
| `HRG` | `/committees/board/hr_governance` | `-HR-_-Governance-Committee` | `2002` |
| `TS` | `/committees/board/tech-security` | `-Technology-_-Security-Committee` | `2023` |

### TAC and sub-groups

| Abbrev | URL path | Slug regex | `year_start` |
|--------|----------|------------|--------------|
| `TAC` | `/committees/tac` | `(?:-TAC-Meeting\|-Special-TAC-Meeting)` | `2002` |
| `LLWG` | `/committees/tac/llwg` | `-LLWG-Meeting` | `2025` |
| `CFSG` | `/committees/tac/cfsg` | `-CFSG-Meeting` | `2023` |
| `RTCBTF` | `/committees/inactive/rtcbtf` | `-RTCBTF-Meeting` | `2023` |

### Subcommittees

| Abbrev | URL path | Slug regex | `year_start` |
|--------|----------|------------|--------------|
| `PRS` | `/committees/prs` | `-PRS-Meeting` | `2010` |
| `RMS` | `/committees/rms` | `-RMS-Meeting` | `2010` |
| `TDTMS` | `/committees/rms/tdtms` | `-TDTMS-Meeting` | `2015` |
| `RMTTF` | `/committees/rms/rmttf` | `-RMTTF-Meeting` | `2015` |
| `ROS` | `/committees/ros` | `-ROS-Meeting` | `2010` |
| `WMS` | `/committees/wms` | `-WMS-Meeting` | `2010` |

### ROS working groups

| Abbrev | URL path | Slug regex | `year_start` |
|--------|----------|------------|--------------|
| `BSWG` | `/committees/ros/bswg` | `-BSWG-Meeting` | `2002` |
| `DWG` | `/committees/ros/dwg` | `-DWG-Meeting` | `2003` |
| `IBRWG` | `/committees/ros/ibrwg` | `-IBRWG-Meeting` | `2023` |
| `MWG` | `/committees/ros/mwg` | `-MWG-Meeting` | `2002` |
| `NDSWG` | `/committees/ros/ndswg` | `-NDSWG-Meeting` | `2002` |
| `OWG` | `/committees/ros/owg` | `-OWG-Meeting` | verify |
| `OTWG` | `/committees/ros/otwg` | `-OTWG-Meeting` | verify |
| `PDCWG` | `/committees/ros/pdcwg` | `-PDCWG-Meeting` | verify |
| `PLWG` | `/committees/ros/plwg` | `-PLWG-Meeting` | `2010` |
| `SPWG` | `/committees/ros/spwg` | `-SPWG-Meeting` | verify |
| `SSWG` | `/committees/ros/sswg` | `-SSWG-Meeting` | verify |
| `VPWG` | `/committees/ros/vpwg` | `-VPWG-Meeting` | verify |

### WMS working groups

| Abbrev | URL path | Slug regex | `year_start` |
|--------|----------|------------|--------------|
| `CMWG` | `/committees/wms/cmwg` | `-CMWG-Meeting` | `2010` |
| `DSWG` | `/committees/wms/dswg` | `-DSWG-Meeting` | `2002` |
| `SAWG` | `/committees/wms/sawg` | `-SAWG-Meeting` | `2015` |
| `WMWG` | `/committees/wms/wmwg` | `-WMWG-Meeting` | `2019` |

### Inactive

| Abbrev | URL path | Slug regex | Notes |
|--------|----------|------------|-------|
| `IBRTF` | `/committees/inactive/ibrtf` | `-IBRTF-Meeting` | 2022 only; set `no_year_pages: True` |

> **All base URLs** are relative to `https://www.ercot.com`. The slug regex is matched against the `href` of `<a>` tags on the year page. A `-_-Webex` suffix may appear in calendar URLs for virtual meetings — it is harmless and does not need to be in the slug regex.

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
| Duplicate meetings from overlapping year pages | `run_committee` deduplicates by calendar URL before processing |
