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


def process_meetings(meetings: list[tuple[str, str]], base_dir: str) -> tuple[int, int, int]:
    total_ok = total_skip = total_err = 0
    for date_iso, cal_url in meetings:
        folder = os.path.join(base_dir, date_iso)
        print(f"  [{date_iso}]  {cal_url}")
        doc_links = get_document_links(cal_url)
        time.sleep(REQUEST_DELAY)
        if not doc_links:
            print("    (no downloadable documents found)")
            continue
        print(f"    {len(doc_links)} document(s)  ->  {folder}")
        os.makedirs(folder, exist_ok=True)
        for url in doc_links:
            fname = sanitize(unquote(os.path.basename(urlparse(url).path)))
            if not fname:
                fname = "document.bin"
            fname = safe_fname(fname, folder)
            result = download_file(url, os.path.join(folder, fname))
            if result == "ok":
                total_ok += 1
            elif result == "skip":
                total_skip += 1
            else:
                total_err += 1
            time.sleep(REQUEST_DELAY)
    return total_ok, total_skip, total_err


def run_committee(abbrev: str, cfg: dict) -> tuple[int, int, int]:
    base_dir = os.path.join(BASE_ROOT, abbrev)
    year_start = cfg["year_start"]
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


def main():
    target = list(COMMITTEES.keys()) if COMMITTEES_TO_RUN is None else COMMITTEES_TO_RUN
    grand_ok = grand_skip = grand_err = 0

    print(f"ERCOT Stakeholder Meeting Downloader — {len(target)} committee(s)")
    print(f"Year range: up to {YEAR_END}")

    for abbrev in target:
        if abbrev not in COMMITTEES:
            print(f"\n[WARN] Unknown committee '{abbrev}' — skipping.")
            continue
        ok, skip, err = run_committee(abbrev, COMMITTEES[abbrev])
        grand_ok += ok
        grand_skip += skip
        grand_err += err

    print(f"\n{'='*60}")
    print(f"All done.  Downloaded: {grand_ok}  |  Skipped: {grand_skip}  |  Errors: {grand_err}")


if __name__ == "__main__":
    main()
