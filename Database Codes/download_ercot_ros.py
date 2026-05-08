"""
ERCOT ROS Document Downloader
==============================
Fetches meeting documents from the ERCOT Reliability and Operations
Subcommittee (ROS) for a configurable year range, and saves them to a
per-meeting date folder.

Usage
-----
    pip install requests beautifulsoup4
    python download_ercot_ros.py

Configuration
-------------
Edit the SETTINGS block below to change where files are saved, adjust
the year range, or limit to specific meeting dates.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
from urllib.parse import urljoin, unquote, urlparse

# ── SETTINGS ─────────────────────────────────────────────────────────────────

# Year range to process (both ends inclusive).
YEAR_START = 2010
YEAR_END   = date.today().year

# Override: list of specific ISO meeting dates to process instead of all years.
# Leave as None to auto-fetch.  Example: ["2025-01-09", "2025-03-06"]
MEETING_DATES = None

# Root folder where files are saved: BASE_DIR/YYYY-MM-DD/<filename>
BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS\ROS"

# Seconds to pause between HTTP requests.
REQUEST_DELAY = 1.0

# File extensions to download.
DOWNLOAD_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".pptx", ".ppt", ".zip"}

# ─────────────────────────────────────────────────────────────────────────────

BASE_URL     = "https://www.ercot.com"
ROS_BASE_URL = "https://www.ercot.com/committees/ros"

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


def year_page_url(year: int) -> str:
    return ROS_BASE_URL if year == date.today().year else f"{ROS_BASE_URL}/{year}"


def get_meeting_urls(year: int) -> list[tuple[str, str]]:
    """Fetch the ROS year page and return (date_iso, calendar_url) for non-cancelled meetings."""
    url = year_page_url(year)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [ERR] Could not fetch {url}: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    meetings, seen = [], set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/calendar/" not in href:
            continue
        m = re.search(r"/calendar/(\d{8})-ROS", href, re.IGNORECASE)
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
            print(f"  [SKIP] {d.isoformat()} — cancelled")
            continue

        seen.add(full_url)
        meetings.append((d.isoformat(), full_url))

    return sorted(meetings)


def get_document_links(calendar_url: str) -> list[str]:
    """Fetch an ERCOT meeting calendar page and return downloadable document URLs."""
    try:
        resp = requests.get(calendar_url, headers=HEADERS, timeout=20)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [WARN] Could not fetch {calendar_url}: {exc}")
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
    """Download url to dest_path using a temp file. Returns 'ok', 'skip', or 'err'."""
    filename = os.path.basename(dest_path)
    if os.path.exists(dest_path):
        print(f"  [SKIP] {filename}")
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
        print(f"  [OK]   {filename}  ({size_kb:.1f} KB)")
        return "ok"
    except (requests.RequestException, OSError) as exc:
        print(f"  [ERR]  {filename} — {exc}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return "err"


def process_meetings(meetings: list[tuple[str, str]]) -> tuple[int, int, int]:
    total_ok = total_skip = total_err = 0
    for date_iso, cal_url in meetings:
        folder = os.path.join(BASE_DIR, date_iso)
        print(f"\n[ROS {date_iso}]  {cal_url}")
        doc_links = get_document_links(cal_url)
        time.sleep(REQUEST_DELAY)
        if not doc_links:
            print("  (no downloadable documents found)")
            continue
        print(f"  {len(doc_links)} document(s)  ->  {folder}")
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


def main():
    if MEETING_DATES:
        print(f"ERCOT ROS Document Downloader  (manual dates: {len(MEETING_DATES)} meeting(s))")
        years = sorted({int(d[:4]) for d in MEETING_DATES})
        all_meetings = []
        for yr in years:
            all_meetings.extend(get_meeting_urls(yr))
            time.sleep(REQUEST_DELAY)
        meetings = [(d, u) for d, u in all_meetings if d in set(MEETING_DATES)]
    else:
        print(f"ERCOT ROS Document Downloader  ({YEAR_START}–{YEAR_END})")
        meetings = []
        for year in range(YEAR_START, YEAR_END + 1):
            print(f"Fetching ROS {year} from {year_page_url(year)} ...")
            yr_meetings = get_meeting_urls(year)
            print(f"  Found {len(yr_meetings)} meeting(s).")
            meetings.extend(yr_meetings)
            time.sleep(REQUEST_DELAY)

    print(f"\nTotal meetings to process: {len(meetings)}")
    print("=" * 60)

    ok, skip, err = process_meetings(meetings)

    print(f"\n{'='*60}")
    print(f"Done.  Downloaded: {ok}  |  Skipped: {skip}  |  Errors: {err}")


if __name__ == "__main__":
    main()
