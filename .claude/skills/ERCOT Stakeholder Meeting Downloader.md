---
name: ERCOT-Stakeholder-Meeting-Downloader
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

One sub-folder per meeting date. Regular documents are never overwritten — only
new files are added. **Bundled `.zip` files are unzipped into the same meeting
date folder and then removed** (see "Unzipping bundled documents" below); files
extracted from a zip *do* overwrite same-named duplicates.

The script covers 34 committees across these groups:

| Group | Committees |
|-------|-----------|
| Board | BOARD, FA, HRG, TS |
| TAC | TAC, LLWG, CFSG, RTCBTF |
| Subcommittees | PRS, RMS, TDTMS, TXSETLP, RMTTF, ROS, WMS |
| ROS working groups | BSWG, DWG, IBRWG, MWG, NDSWG, OWG, OTWG, PDCWG, PLWG, SPWG, SSWG, VPWG |
| WMS working groups | CMWG, DSWG, SAWG, WMWG |
| Inactive | IBRTF, BESTF, TXSET |

Added 2026-06-17/18 (all `no_year_pages`): `BESTF` (Battery Energy Storage Task
Force, `/committees/inactive/bestf`, slug `-BESTF-Meeting`), `TXSET` (Texas SET
WG, `/committees/inactive/txset`, slug `Texas-SET`), and `TXSETLP` (the **active**
Texas SET/Load Profiling WG, `/committees/rms/txsetlp`, slug `Texas-SET_LP`).
`TXSETLP` is the successor that absorbed the old Load Profiling (LPWG) and Texas
SET work; it has no `/YEAR` archive, so it's tracked via `no_year_pages`.

**Folders that cannot be auto-filled** (confirmed against live ercot.com,
2026-06-17): `MSWG`, `PWG`, `RCWG` have inactive pages but expose **no
`/calendar/` meeting links**, so the downloader finds nothing — their empty
folders remain. The phantom folders `LPWG`, `PDVWG`, `TDTMSTF`, `TXSETWG` (no
ercot.com page anywhere) were **deleted 2026-06-18**.

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
4. For each meeting, **pre-computes new vs already-saved files** (the
   market-rules accounting pattern) and prints `N file(s) already up to date` /
   `M new file(s) (out of T total)`, then downloads only the new ones via
   streaming (64 KB chunks), `.tmp` → rename on success.
5. **Unzips any bundled `.zip` documents** into the same meeting date folder via
   `extract_zips(folder)` (see below).
6. Prints a per-committee and grand total summary: Downloaded (new files across
   N meetings) | Skipped | Errors.
7. **Emits a coverage report** over the whole database (see below).

## Unzipping bundled documents

ERCOT often posts a `Meeting-Materials-*.zip` and `Revision-Requests-*.zip`
bundle per meeting. After downloading a meeting's files, `extract_zips(folder)`
runs for that meeting date folder and:

1. **Unzips** every `.zip` into the **same meeting date folder**, *flattened* —
   any internal sub-folders in the archive are dropped so all files land
   directly under `YYYY-MM-DD/`.
2. **Overwrites duplicates** — a file extracted from the zip replaces a
   same-named file already in the folder (the zip is treated as authoritative).
3. **Removes the zip** afterwards, leaving a tiny `<zip-name>.extracted` marker.

The marker lets routine **incremental** runs skip the zip instead of
re-downloading and re-extracting it every time (the new-vs-saved pre-check
treats `dest` *or* `dest + ".extracted"` as already present). The marker is
excluded from the meeting manifests and profiles, so it never appears in the
document list. A corrupt archive is left in place and logged `[ZIP-ERR]`.

> **One-time backfill of existing zips.** `extract_zips` only runs for meetings
> the downloader processes (incremental = current year). To unzip zips already
> on disk in older folders, run a full pass (`SINCE_YEAR = None`) or extract
> directly, e.g.:
> ```python
> import os, download_ercot_stkhdr as d
> for root, _, files in os.walk(d.BASE_ROOT):
>     if any(f.lower().endswith(".zip") for f in files):
>         d.extract_zips(root)
> ```
> Then regenerate manifests/profiles so the newly surfaced files appear.

## Revision requests stay in Paper Trails (not the meeting list)

Revision-request paperwork (NPRR, NOGRR, PGRR, SCR, COPMGRR, RMGRR — and the
sibling types RRGRR, OBDRR, VCMRR, SMOGRR) belongs in the **Paper Trails**
section, not the meeting document list. So:

1. **Revision-request bundles are never unzipped.** `extract_zips` skips any zip
   whose name carries a category code or `Revision-Request(s)` (`RR_ZIP_RE`),
   logging `[ZIP-KEEP]`. They remain as `.zip` (already hidden from the lists).
2. **Loose revision-request packet files are removed.**
   `remove_revision_request_files(folder)` deletes files whose name *starts with*
   a revision-request id — number-first `1214NPRR-16 …`, `055OBDRR-02 …` or
   category-first `NPRR078 Impact Analysis.doc` (`RR_FILE_RE`). It runs after
   `extract_zips` on every processed meeting.
   - **Kept:** numbered agenda items (`10.-…`), date-prefixed meeting files
     (`2026-TAC-…Ballot…`), and presentation decks (`.ppt`/`.pptx`, even when
     titled after an RR like `NPRR1325_Overview.pptx` or `NOGRR282 Update.pptx`).
3. **Regenerate the file lists** afterwards (`gen_stkhdr_manifest.py` and, for
   the meeting summaries, `gen_stkhdr_profiles.py`) so the meeting-date document
   lists reflect the removals.

> **One-time cleanup of already-extracted RR files** (e.g. after a zip backfill):
> ```python
> import os, re, download_ercot_stkhdr as d
> for root, _, _ in os.walk(d.BASE_ROOT):
>     if re.search(r"\d{4}-\d{2}-\d{2}$", os.path.basename(root)):
>         d.remove_revision_request_files(root)
> ```
> Then regenerate manifests and profiles.

The default scope is **incremental** (`SINCE_YEAR` = current year). For a full
backfill, set `SINCE_YEAR = None`.

## Coverage Report

After the download pass, `coverage_report(BASE_ROOT, COMMITTEES)` scans the
database on disk and prints — and writes to
`BASE_ROOT/coverage_report_YYYYMMDD.txt` — a manifest of what's actually present
(the stakeholder-meetings analog of the market-rules Excel tracker):

- **Populated** committee folders (meeting count + file count), flagging any
  `[NOT IN REGISTRY]`.
- **Empty / non-filled** committee folders, noting whether each is in the
  registry or has no downloader config.
- **Registry committees with no folder on disk.**
- **Meeting folders that exist but hold no files.**

Run it standalone without downloading via:
`python -c "import download_ercot_stkhdr as d; d.coverage_report(d.BASE_ROOT, d.COMMITTEES)"`

---

## SETTINGS Block

| Setting | Default | Purpose |
|---------|---------|---------|
| `COMMITTEES_TO_RUN` | `None` | `None` = all; or list like `["TAC", "WMS"]` to run a subset |
| `YEAR_END` | `date.today().year` | Last year to fetch (inclusive); each committee defines its own `year_start` |
| `MEETING_DATES` | `None` | Override: list of ISO dates to process, e.g. `["2025-01-09"]` |
| `SINCE_YEAR` | `date.today().year` | **Incremental mode** (learned from the market-rules downloaders). Only crawl meetings from this year onward, so routine runs pick up just new meetings instead of re-walking ~20 years of year pages. Set to `None` for a full backfill from each committee's `year_start`. |
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
| `extract_zips(folder)` | Unzips every `.zip` in a meeting date folder (flattened) overwriting duplicates, removes the zip, and leaves a `.extracted` marker. Returns the count extracted |
| `process_meetings(meetings, base_dir)` | Iterates meeting list; pre-counts new vs already-saved files per meeting, downloads only new ones. Returns `(ok, skip, err, meetings_updated)` |
| `run_committee(abbrev, cfg)` | Full year-loop + meeting-download for one committee; clamps `year_start` to `SINCE_YEAR` when set. Returns `(ok, skip, err, meetings_updated)` |
| `coverage_report(root, registry)` | Scans the DB on disk; reports populated vs empty folders and registry/disk mismatches; writes `coverage_report_YYYYMMDD.txt` |
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

For the full in-scope committee list see `ERCOT Stakeholder Meetings Links.md`. Key values for adding new entries:

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
