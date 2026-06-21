"""
ERCOT Stakeholder Committee Meeting Downloader
==============================================
Downloads meeting documents for all (or selected) ERCOT stakeholder committees.
For each committee it scrapes the year pages on ercot.com/committees, collects
calendar page URLs for each non-cancelled meeting, and downloads only files not
yet saved locally (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, ZIP).

Usage
-----
    pip install requests beautifulsoup4
    python "Database Codes/download_STKHDR_Meets/download_ercot_stkhdr.py"

Configuration
-------------
Edit the SETTINGS block below to limit to specific committees or meeting dates.
"""

import os
import re
import time
import zipfile
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
from urllib.parse import urljoin, unquote, urlparse

# ── SETTINGS ──────────────────────────────────────────────────────────────────

# Set to a list to run only those committees, e.g. ["TAC", "WMS", "PRS"].
# None = run every committee in the registry below.
COMMITTEES_TO_RUN = None

# Last year to fetch (inclusive). Each committee defines its own year_start.
YEAR_END = date.today().year

# Override: list of ISO meeting dates to process across all committees.
# Leave as None to auto-fetch all meetings in the year range.
# Example: MEETING_DATES = ["2025-01-09", "2025-03-06"]
MEETING_DATES = None

# Incremental mode (learned from the market-rules downloaders, which only
# process issues not already tracked). Only crawl meetings from this year
# onward, so routine runs pick up just the new meetings instead of re-walking
# two decades of year pages. Set to None for a full backfill from each
# committee's year_start.
SINCE_YEAR = date.today().year

# Root folder; each committee gets BASE_ROOT/<ABBREV>/YYYY-MM-DD/<files>
BASE_ROOT = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS"

# Seconds to pause between HTTP requests.
REQUEST_DELAY = 1.0

# File extensions to download.
DOWNLOAD_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx", ".ppt", ".zip"}

# ──────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.ercot.com"

# Committee registry.  Keys are the folder name under BASE_ROOT.
# no_year_pages=True: committee has no /YEAR sub-pages — always fetch the main URL.
COMMITTEES = {
    # ── Board ──────────────────────────────────────────────────────────────────
    "BOARD":   {"url": f"{BASE_URL}/committees/board",                  "slug": r"-Board-of-Directors-Meeting",           "year_start": 2002},
    "FA":      {"url": f"{BASE_URL}/committees/board/finance_audit",    "slug": r"-Finance-_-Audit-Committee",            "year_start": 2004},
    "HRG":     {"url": f"{BASE_URL}/committees/board/hr_governance",    "slug": r"-HR-_-Governance-Committee",            "year_start": 2002},
    "TS":      {"url": f"{BASE_URL}/committees/board/tech-security",    "slug": r"-Technology-_-Security-Committee",      "year_start": 2023},
    # ── TAC ────────────────────────────────────────────────────────────────────
    "TAC":     {"url": f"{BASE_URL}/committees/tac",                    "slug": r"(?:-TAC-Meeting|-Special-TAC-Meeting)", "year_start": 2002},
    "LLWG":    {"url": f"{BASE_URL}/committees/tac/llwg",               "slug": r"-LLWG-Meeting",                         "year_start": 2025},
    "CFSG":    {"url": f"{BASE_URL}/committees/tac/cfsg",               "slug": r"-CFSG-Meeting",                         "year_start": 2023},
    "RTCBTF":  {"url": f"{BASE_URL}/committees/inactive/rtcbtf",        "slug": r"-RTCBTF-Meeting",                       "year_start": 2023},
    # ── Subcommittees ──────────────────────────────────────────────────────────
    "PRS":     {"url": f"{BASE_URL}/committees/prs",                    "slug": r"-PRS-Meeting",                          "year_start": 2010},
    "RMS":     {"url": f"{BASE_URL}/committees/rms",                    "slug": r"-RMS-Meeting",                          "year_start": 2010},
    "TDTMS":   {"url": f"{BASE_URL}/committees/rms/tdtms",              "slug": r"-TDTMS-Meeting",                        "year_start": 2015},
    "TXSETLP": {"url": f"{BASE_URL}/committees/rms/txsetlp",            "slug": r"Texas-SET_LP",                          "year_start": 2024, "no_year_pages": True},
    "RMTTF":   {"url": f"{BASE_URL}/committees/rms/rmttf",              "slug": r"-RMTTF-Meeting",                        "year_start": 2015},
    "ROS":     {"url": f"{BASE_URL}/committees/ros",                    "slug": r"-ROS-Meeting",                          "year_start": 2010},
    "WMS":     {"url": f"{BASE_URL}/committees/wms",                    "slug": r"-WMS-Meeting",                          "year_start": 2010},
    # ── ROS working groups ─────────────────────────────────────────────────────
    "BSWG":    {"url": f"{BASE_URL}/committees/ros/bswg",               "slug": r"-BSWG-Meeting",                         "year_start": 2002},
    "DWG":     {"url": f"{BASE_URL}/committees/ros/dwg",                "slug": r"-DWG-Meeting",                          "year_start": 2003},
    "IBRWG":   {"url": f"{BASE_URL}/committees/ros/ibrwg",              "slug": r"-IBRWG-Meeting",                        "year_start": 2023},
    "MWG":     {"url": f"{BASE_URL}/committees/ros/mwg",                "slug": r"-MWG-Meeting",                          "year_start": 2002},
    "NDSWG":   {"url": f"{BASE_URL}/committees/ros/ndswg",              "slug": r"-NDSWG-Meeting",                        "year_start": 2002},
    "OWG":     {"url": f"{BASE_URL}/committees/ros/owg",                "slug": r"-OWG-Meeting",                          "year_start": 2002},
    "OTWG":    {"url": f"{BASE_URL}/committees/ros/otwg",               "slug": r"-OTWG-Meeting",                         "year_start": 2002},
    "PDCWG":   {"url": f"{BASE_URL}/committees/ros/pdcwg",              "slug": r"-PDCWG-Meeting",                        "year_start": 2002},
    "PLWG":    {"url": f"{BASE_URL}/committees/ros/plwg",               "slug": r"-PLWG-Meeting",                         "year_start": 2010},
    "SPWG":    {"url": f"{BASE_URL}/committees/ros/spwg",               "slug": r"-SPWG-Meeting",                         "year_start": 2002},
    "SSWG":    {"url": f"{BASE_URL}/committees/ros/sswg",               "slug": r"-SSWG-Meeting",                         "year_start": 2002},
    "VPWG":    {"url": f"{BASE_URL}/committees/ros/vpwg",               "slug": r"-VPWG-Meeting",                         "year_start": 2002},
    # ── WMS working groups ─────────────────────────────────────────────────────
    "CMWG":    {"url": f"{BASE_URL}/committees/wms/cmwg",               "slug": r"-CMWG-Meeting",                         "year_start": 2010},
    "DSWG":    {"url": f"{BASE_URL}/committees/wms/dswg",               "slug": r"-DSWG-Meeting",                         "year_start": 2002},
    "SAWG":    {"url": f"{BASE_URL}/committees/wms/sawg",               "slug": r"-SAWG-Meeting",                         "year_start": 2015},
    "WMWG":    {"url": f"{BASE_URL}/committees/wms/wmwg",               "slug": r"-WMWG-Meeting",                         "year_start": 2019},
    # ── Inactive ───────────────────────────────────────────────────────────────
    "IBRTF":   {"url": f"{BASE_URL}/committees/inactive/ibrtf",         "slug": r"-IBRTF-Meeting",                        "year_start": 2022, "no_year_pages": True},
    "BESTF":   {"url": f"{BASE_URL}/committees/inactive/bestf",         "slug": r"-BESTF-Meeting",                        "year_start": 2019, "no_year_pages": True},
    "TXSET":   {"url": f"{BASE_URL}/committees/inactive/txset",         "slug": r"Texas-SET",                             "year_start": 2025, "no_year_pages": True},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.ercot.com/",
}

MAX_PATH = 240


def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def safe_fname(fname: str, dest_dir: str) -> str:
    stem, ext = os.path.splitext(fname)
    max_stem = MAX_PATH - len(dest_dir) - len(os.sep) - len(ext)
    if max_stem < 1:
        max_stem = 1
    return stem[:max_stem] + ext


def year_page_url(year: int, base_url: str, no_year_pages: bool = False) -> str:
    if no_year_pages or year == date.today().year:
        return base_url
    return f"{base_url}/{year}"


def get_meeting_urls(year: int, cfg: dict) -> list[tuple[str, str]]:
    url = year_page_url(year, cfg["url"], cfg.get("no_year_pages", False))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    [ERR] Could not fetch {url}: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    slug_re = re.compile(cfg["slug"], re.IGNORECASE)
    date_re = re.compile(r"/calendar/(\d{8})", re.IGNORECASE)
    meetings, seen = [], set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/calendar/" not in href or not slug_re.search(href):
            continue
        m = date_re.search(href)
        if not m:
            continue
        full_url = urljoin(BASE_URL, href)
        if full_url in seen:
            continue
        try:
            d = datetime.strptime(m.group(1), "%m%d%Y").date()
        except ValueError:
            continue

        parent_text = (a.parent.get_text(" ", strip=True) if a.parent else "").upper()
        if "CANCELLED" in parent_text or "CANCELED" in parent_text:
            print(f"    [SKIP] {d.isoformat()} — cancelled")
            continue

        seen.add(full_url)
        meetings.append((d.isoformat(), full_url))

    return sorted(meetings)


def get_document_links(calendar_url: str) -> list[str]:
    try:
        resp = requests.get(calendar_url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"    [WARN] Could not fetch {calendar_url}: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links, seen = [], set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        ext = os.path.splitext(urlparse(href).path)[-1].lower()
        if ext not in DOWNLOAD_EXTS:
            continue
        full_url = urljoin(BASE_URL, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        links.append(full_url)

    return links


def download_file(url: str, dest_path: str) -> str:
    filename = os.path.basename(dest_path)
    if os.path.exists(dest_path):
        print(f"    [SKIP] {filename}")
        return "skip"
    tmp_path = dest_path + ".tmp"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(tmp_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                fh.write(chunk)
        os.replace(tmp_path, dest_path)
        size_kb = os.path.getsize(dest_path) / 1024
        print(f"    [OK]   {filename}  ({size_kb:.1f} KB)")
        return "ok"
    except (requests.RequestException, OSError) as exc:
        print(f"    [ERR]  {filename} — {exc}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return "err"


def extract_zips(folder: str) -> int:
    """Unzip every .zip in `folder` into that same meeting-date folder, then
    delete the zip. Behavior:
      1) extract members (flattened — internal sub-folders are dropped) into the
         meeting date folder;
      2) overwrite any duplicate files already present;
      3) remove the zip afterwards, leaving a small '<zip>.extracted' marker so
         routine incremental runs don't re-download and re-extract it.
    A corrupt zip is left in place. Returns the number of zips extracted.
    """
    if not os.path.isdir(folder):
        return 0
    extracted = 0
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".zip"):
            continue
        zpath = os.path.join(folder, fn)
        try:
            with zipfile.ZipFile(zpath) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    base = sanitize(os.path.basename(member.filename))
                    if not base:                      # skip empty/odd entries
                        continue
                    dest = os.path.join(folder, safe_fname(base, folder))
                    with zf.open(member) as src, open(dest, "wb") as out:  # overwrite dupes
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            out.write(chunk)
            open(zpath + ".extracted", "w").close()   # marker (excluded from manifests)
            os.remove(zpath)
            extracted += 1
            print(f"    [UNZIP] {fn} -> extracted into folder and removed")
        except (zipfile.BadZipFile, OSError) as exc:
            print(f"    [ZIP-ERR] {fn} left in place — {exc}")
    return extracted


def process_meetings(meetings: list[tuple[str, str]], base_dir: str) -> tuple[int, int, int, int]:
    """Download new documents for each meeting. Mirrors the market-rules
    downloaders: pre-computes new vs already-saved files per meeting and only
    fetches the new ones. Returns (downloaded, skipped, errors, meetings_updated)."""
    total_ok = total_skip = total_err = meetings_updated = 0
    for date_iso, cal_url in meetings:
        folder = os.path.join(base_dir, date_iso)
        print(f"  [{date_iso}]  {cal_url}")
        doc_links = get_document_links(cal_url)
        time.sleep(REQUEST_DELAY)
        if not doc_links:
            print("    (no downloadable documents found)")
            extract_zips(folder)          # clear any leftover zips
            continue

        new_items = []
        for url in doc_links:
            fname = sanitize(unquote(os.path.basename(urlparse(url).path))) or "document.bin"
            fname = safe_fname(fname, folder)
            dest = os.path.join(folder, fname)
            # A zip already extracted on a prior run leaves a '.extracted' marker;
            # treat that (or the file itself) as already present.
            if os.path.exists(dest) or os.path.exists(dest + ".extracted"):
                total_skip += 1
            else:
                new_items.append((url, dest))

        already = len(doc_links) - len(new_items)
        if already:
            print(f"    {already} file(s) already up to date.")
        if new_items:
            print(f"    {len(new_items)} new file(s) (out of {len(doc_links)} total)  ->  {folder}")
            os.makedirs(folder, exist_ok=True)
            meetings_updated += 1
            for url, dest in new_items:
                result = download_file(url, dest)
                if result == "ok":
                    total_ok += 1
                else:
                    total_err += 1
                time.sleep(REQUEST_DELAY)
        else:
            print("    Nothing new to download.")

        # Unzip any bundled documents (newly downloaded or left over) into the
        # meeting-date folder, overwriting duplicates and removing the zip.
        extract_zips(folder)
    return total_ok, total_skip, total_err, meetings_updated


def run_committee(abbrev: str, cfg: dict) -> tuple[int, int, int, int]:
    base_dir = os.path.join(BASE_ROOT, abbrev)
    year_start = cfg["year_start"]
    if SINCE_YEAR is not None:
        year_start = max(year_start, SINCE_YEAR)
    no_year = cfg.get("no_year_pages", False)

    print(f"\n{'='*60}")
    print(f"[{abbrev}]  {cfg['url']}")
    print(f"{'='*60}")

    if MEETING_DATES:
        years = sorted({int(d[:4]) for d in MEETING_DATES})
        filter_dates = set(MEETING_DATES)
    else:
        years = list(range(year_start, YEAR_END + 1))
        filter_dates = None

    all_meetings = []
    for yr in years:
        print(f"  Fetching {abbrev} {yr} ...")
        yr_meets = get_meeting_urls(yr, cfg)
        print(f"    Found {len(yr_meets)} meeting(s).")
        all_meetings.extend(yr_meets)
        time.sleep(REQUEST_DELAY)
        if no_year:
            break

    if filter_dates:
        all_meetings = [(d, u) for d, u in all_meetings if d in filter_dates]

    # Deduplicate (different year pages can list the same meeting)
    seen = set()
    deduped = []
    for item in all_meetings:
        if item[1] not in seen:
            seen.add(item[1])
            deduped.append(item)
    all_meetings = sorted(deduped)

    print(f"  Total meetings to process: {len(all_meetings)}")
    return process_meetings(all_meetings, base_dir)


def coverage_report(root: str, registry: dict, write_file: bool = True) -> str:
    """Scan BASE_ROOT and summarize which committee folders are populated vs
    empty, list date folders that exist but hold no files, and reconcile the
    on-disk folders against the committee registry. Returns the report text and
    (optionally) writes it to a timestamped file under BASE_ROOT.

    This is the stakeholder-meetings analog of the market-rules Excel tracker:
    a manifest of what is actually present on disk."""
    lines = []
    def out(s=""):
        lines.append(s)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out(f"ERCOT Stakeholder Meetings — Coverage Report  ({ts})")
    out(f"Root: {root}")
    out("=" * 70)

    if not os.path.isdir(root):
        out("[ERR] Root folder does not exist.")
        report = "\n".join(lines)
        print(report)
        return report

    disk_dirs = sorted(d for d in os.listdir(root)
                       if os.path.isdir(os.path.join(root, d)))
    registry_keys = set(registry.keys())

    populated, empty = [], []
    partial_dates = {}  # committee -> [date folders with no files]
    file_total = 0

    for abbrev in disk_dirs:
        cdir = os.path.join(root, abbrev)
        date_dirs = [d for d in os.listdir(cdir)
                     if os.path.isdir(os.path.join(cdir, d))]
        empties = []
        cfiles = 0
        for d in date_dirs:
            ddir = os.path.join(cdir, d)
            n = sum(1 for f in os.listdir(ddir)
                    if os.path.isfile(os.path.join(ddir, f)) and not f.endswith(".tmp"))
            cfiles += n
            if n == 0:
                empties.append(d)
        file_total += cfiles
        if date_dirs and cfiles > 0:
            populated.append((abbrev, len(date_dirs), cfiles))
        else:
            empty.append((abbrev, len(date_dirs)))
        if empties:
            partial_dates[abbrev] = sorted(empties)

    out(f"\nPOPULATED committee folders ({len(populated)}):")
    for abbrev, nmeet, nfiles in populated:
        reg = "" if abbrev in registry_keys else "   [NOT IN REGISTRY]"
        out(f"  {abbrev:<10} {nmeet:>4} meeting(s)  {nfiles:>6} file(s){reg}")

    out(f"\nEMPTY / NON-FILLED committee folders ({len(empty)}):")
    if empty:
        for abbrev, nmeet in empty:
            reg = "in registry" if abbrev in registry_keys else "NOT in registry — no downloader config"
            detail = f"{nmeet} meeting folder(s), 0 files" if nmeet else "no meeting folders"
            out(f"  {abbrev:<10} {detail}  ({reg})")
    else:
        out("  (none)")

    missing = sorted(registry_keys - set(disk_dirs))
    out(f"\nRegistry committees with NO folder on disk ({len(missing)}):")
    out("  " + (", ".join(missing) if missing else "(none)"))

    if partial_dates:
        out(f"\nMeeting folders that exist but contain NO files:")
        for abbrev in sorted(partial_dates):
            out(f"  {abbrev}: {', '.join(partial_dates[abbrev])}")

    out("\n" + "=" * 70)
    out(f"Totals: {len(disk_dirs)} committee folder(s), "
        f"{len(populated)} populated, {len(empty)} empty, {file_total} file(s).")

    report = "\n".join(lines)
    print("\n" + report)
    if write_file:
        path = os.path.join(root, f"coverage_report_{datetime.now().strftime('%Y%m%d')}.txt")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(report + "\n")
            print(f"\n[report] written to {path}")
        except OSError as exc:
            print(f"\n[report] could not write file: {exc}")
    return report


def main():
    target = list(COMMITTEES.keys()) if COMMITTEES_TO_RUN is None else COMMITTEES_TO_RUN
    grand_ok = grand_skip = grand_err = grand_meet = 0

    print(f"ERCOT Stakeholder Meeting Downloader — {len(target)} committee(s)")
    print(f"Year range: {SINCE_YEAR if SINCE_YEAR is not None else 'full history'} .. {YEAR_END}")

    for abbrev in target:
        if abbrev not in COMMITTEES:
            print(f"\n[WARN] Unknown committee '{abbrev}' — skipping.")
            continue
        ok, skip, err, meet = run_committee(abbrev, COMMITTEES[abbrev])
        grand_ok += ok
        grand_skip += skip
        grand_err += err
        grand_meet += meet

    print(f"\n{'='*60}")
    print(f"All done.  Downloaded: {grand_ok} new file(s) across {grand_meet} meeting(s)  "
          f"|  Skipped: {grand_skip}  |  Errors: {grand_err}")

    # Coverage report over the full database (not just this run's scope).
    coverage_report(BASE_ROOT, COMMITTEES)


if __name__ == "__main__":
    main()
