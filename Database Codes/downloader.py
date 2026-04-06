"""
downloader.py — Power.Talks
Scrapes ERCOT.com for document hyperlinks and downloads them into the
Documents Database/ folder structure.
"""

import os
import logging
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOWNLOADABLE_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".zip"}

SOURCES = [
    # Market Rules
    {"url": "https://www.ercot.com/mktrules/nprr",   "dest": "Documents Database/ERCOT.MKT.RULES/NPRR"},
    {"url": "https://www.ercot.com/mktrules/nogrr",  "dest": "Documents Database/ERCOT.MKT.RULES/NOGRR"},
    {"url": "https://www.ercot.com/mktrules/pgrr",   "dest": "Documents Database/ERCOT.MKT.RULES/PGRR"},
    {"url": "https://www.ercot.com/mktrules/copmbrr","dest": "Documents Database/ERCOT.MKT.RULES/COPMBRR"},
    {"url": "https://www.ercot.com/mktrules/obdrr",  "dest": "Documents Database/ERCOT.MKT.RULES/OBDRR"},
    {"url": "https://www.ercot.com/mktrules/rmgrr",  "dest": "Documents Database/ERCOT.MKT.RULES/RMGRR"},
    {"url": "https://www.ercot.com/mktrules/rrgrr",  "dest": "Documents Database/ERCOT.MKT.RULES/RRGRR"},
    {"url": "https://www.ercot.com/mktrules/scr",    "dest": "Documents Database/ERCOT.MKT.RULES/SCR"},
    {"url": "https://www.ercot.com/mktrules/smogrr", "dest": "Documents Database/ERCOT.MKT.RULES/SMOGRR"},
    {"url": "https://www.ercot.com/mktrules/vcmrr",  "dest": "Documents Database/ERCOT.MKT.RULES/VCMRR"},
    # Stakeholder Meetings
    {"url": "https://www.ercot.com/committees/board",    "dest": "Documents Database/ERCOT.STKHDR.MEETS/BOARD"},
    {"url": "https://www.ercot.com/committees/bswg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/BSWG"},
    {"url": "https://www.ercot.com/committees/cfsg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/CFSG"},
    {"url": "https://www.ercot.com/committees/cmwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/CMWG"},
    {"url": "https://www.ercot.com/committees/dswg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/DSWG"},
    {"url": "https://www.ercot.com/committees/dwg",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/DWG"},
    {"url": "https://www.ercot.com/committees/ibrwg",    "dest": "Documents Database/ERCOT.STKHDR.MEETS/IBRWG"},
    {"url": "https://www.ercot.com/committees/llwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/LLWG"},
    {"url": "https://www.ercot.com/committees/lpwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/LPWG"},
    {"url": "https://www.ercot.com/committees/mwg",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/MWG"},
    {"url": "https://www.ercot.com/committees/ndswg",    "dest": "Documents Database/ERCOT.STKHDR.MEETS/NDSWG"},
    {"url": "https://www.ercot.com/committees/otwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/OTWG"},
    {"url": "https://www.ercot.com/committees/owg",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/OWG"},
    {"url": "https://www.ercot.com/committees/pdcwg",    "dest": "Documents Database/ERCOT.STKHDR.MEETS/PDCWG"},
    {"url": "https://www.ercot.com/committees/prs",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/PRS"},
    {"url": "https://www.ercot.com/committees/pwg",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/PWG"},
    {"url": "https://www.ercot.com/committees/rms",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/RMS"},
    {"url": "https://www.ercot.com/committees/rmttf",    "dest": "Documents Database/ERCOT.STKHDR.MEETS/RMTTF"},
    {"url": "https://www.ercot.com/committees/ros",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/ROS"},
    {"url": "https://www.ercot.com/committees/rtcbtf",   "dest": "Documents Database/ERCOT.STKHDR.MEETS/RTCBTF"},
    {"url": "https://www.ercot.com/committees/sawg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/SAWG"},
    {"url": "https://www.ercot.com/committees/spwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/SPWG"},
    {"url": "https://www.ercot.com/committees/sswg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/SSWG"},
    {"url": "https://www.ercot.com/committees/tac",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/TAC"},
    {"url": "https://www.ercot.com/committees/tdtmstf",  "dest": "Documents Database/ERCOT.STKHDR.MEETS/TDTMSTF"},
    {"url": "https://www.ercot.com/committees/txsetwg",  "dest": "Documents Database/ERCOT.STKHDR.MEETS/TXSETWG"},
    {"url": "https://www.ercot.com/committees/vpwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/VPWG"},
    {"url": "https://www.ercot.com/committees/wms",      "dest": "Documents Database/ERCOT.STKHDR.MEETS/WMS"},
    {"url": "https://www.ercot.com/committees/wmwg",     "dest": "Documents Database/ERCOT.STKHDR.MEETS/WMWG"},
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "Database Codes", "downloader.log")),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def is_downloadable(url: str) -> bool:
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    return ext in DOWNLOADABLE_EXTENSIONS


def get_links(page_url: str) -> list[str]:
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("Failed to fetch %s: %s", page_url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        absolute = urljoin(page_url, href)
        if is_downloadable(absolute):
            links.append(absolute)
    return links


def download_file(file_url: str, dest_folder: str) -> bool:
    os.makedirs(dest_folder, exist_ok=True)
    filename = os.path.basename(urlparse(file_url).path)
    if not filename:
        return False

    dest_path = os.path.join(dest_folder, filename)
    if os.path.exists(dest_path):
        log.debug("Already exists, skipping: %s", filename)
        return False

    try:
        resp = requests.get(file_url, headers=HEADERS, timeout=60, stream=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        log.info("Downloaded: %s → %s", filename, dest_folder)
        return True
    except requests.RequestException as e:
        log.warning("Failed to download %s: %s", file_url, e)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    total_downloaded = 0
    log.info("=== Downloader started: %s ===", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for source in SOURCES:
        page_url = source["url"]
        dest_folder = os.path.join(BASE_DIR, source["dest"])
        log.info("Scanning: %s", page_url)

        links = get_links(page_url)
        log.info("  Found %d downloadable link(s)", len(links))

        for link in links:
            if download_file(link, dest_folder):
                total_downloaded += 1

    log.info("=== Downloader finished. Total new files: %d ===", total_downloaded)
    return total_downloaded


if __name__ == "__main__":
    run()
