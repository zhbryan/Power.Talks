"""Generate the stakeholder meeting timeline feed for the Meeting Tracks
homepage's "Meeting Timelines" right-panel section.

Scrapes each committee's landing page on ercot.com (which lists the current
year *and* the next year's scheduled meetings) plus, when the window reaches
back into it, the previous year's archive page. Keeps only the meetings inside
a rolling window of +/- WINDOW_DAYS around today and writes a single feed:

    Documents Database/ERCOT.STKHDR.MEETS/_timeline.json

    {
      "generated": "2026-10-20T09:12:00",
      "window_days": 31,
      "from": "2026-09-19", "to": "2026-11-20", "today": "2026-10-20",
      "meeting_count": 48,
      "meetings": [
        { "committee": "TAC", "committee_full_name": "Technical Advisory Committee",
          "date": "2026-10-28", "name": "TAC Meeting",
          "url": "https://www.ercot.com/calendar/10282026-TAC-Meeting",
          "past": false, "on_file": false, "doc_count": 0 },
        ...
      ]
    }

Meetings are ordered oldest first (past at the top, future at the bottom) —
the order the front-end renders top-to-bottom. `on_file`/`doc_count` come from
the local document database, so the panel can tell which meetings already have
downloaded materials.

Cancelled meetings, and rows superseded by a "RESCHEDULED TO <other date>"
note, are dropped.

Run after a download pass (the routine does this automatically):
    python "Database Codes/download_STKHDR_Meets/gen_stkhdr_timeline.py"

Options:
    --window N   days before/after today to include (default 31)
    --quiet      only print the summary line
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Committee registry, HTTP headers and the base URL are shared with the
# downloader so a new committee only has to be registered in one place.
from download_ercot_stkhdr import BASE_ROOT, BASE_URL, COMMITTEES, HEADERS
# Committee full names (abbrev -> (full, chair, vice, model, parent)).
from gen_stkhdr_profiles import C as COMMITTEE_META

OUT_PATH = os.path.join(BASE_ROOT, "_timeline.json")

# Days before and after today to include.
WINDOW_DAYS = 31

# Seconds between HTTP requests (same courtesy delay as the downloader).
REQUEST_DELAY = 1.0

DATE_IN_HREF = re.compile(r"/calendar/(\d{8})", re.IGNORECASE)
RESCHEDULED_TO = re.compile(r"RESCHEDULED\s+TO\s+([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})", re.IGNORECASE)

# Slugs ERCOT writes in all caps that should read as mixed case in the panel.
NAME_FIXUPS = {"TEXAS SET LP": "Texas SET LP", "TEXAS SET": "Texas SET"}

# Conferencing suffixes ERCOT tacks onto calendar slugs ("-_-Webex", "-Webex-Only",
# "-_-Teams"). They say how to attend, not which meeting it is, so they are
# stripped from the display name.
VENUE_SUFFIX_RE = re.compile(
    r"\s*(?:&|and)?\s*(?:web\s?ex|ms\s?teams|teams|zoom)(?:\s+only)?\s*$",
    re.IGNORECASE,
)


def meeting_name(href: str) -> str:
    """Human-readable meeting name from a calendar URL slug.

    '/calendar/10282026-TAC-Meeting'        -> 'TAC Meeting'
    '/calendar/08262026-TAC-Meeting-_-Webex'-> 'TAC Meeting'   (venue suffix dropped)
    '/calendar/04222026-Special-PRS-Meeting'-> 'Special PRS Meeting'
    """
    slug = href.rstrip("/").split("/calendar/")[-1]
    slug = re.sub(r"^\d{8}-?", "", slug)          # drop the MMDDYYYY prefix
    slug = slug.replace("-_-", " & ")             # ERCOT writes '&' as '_'
    slug = slug.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", slug).strip()
    # Drop the "& Webex" / "Webex Only" tail, but never the whole name.
    stripped = VENUE_SUFFIX_RE.sub("", name).strip()
    name = stripped or name or "Meeting"
    for bad, good in NAME_FIXUPS.items():
        if name.startswith(bad):
            name = good + name[len(bad):]
            break
    return name


def _parse_resched(parent_text: str):
    """The date a 'RESCHEDULED TO <date>' note points at, or None."""
    m = RESCHEDULED_TO.search(parent_text or "")
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", "")
    for fmt in ("%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def year_pages(cfg: dict, lo: date, hi: date) -> list[str]:
    """Pages to scrape for the window. The landing page carries the current and
    next year; only a window reaching into last year needs the archive page."""
    pages = [cfg["url"]]
    if not cfg.get("no_year_pages") and lo.year < date.today().year:
        pages.append(f"{cfg['url']}/{lo.year}")
    return pages


def scrape_committee(abbrev: str, cfg: dict, lo: date, hi: date, quiet: bool) -> list[dict]:
    slug_re = re.compile(cfg["slug"], re.IGNORECASE)
    found: dict[tuple[str, str], dict] = {}

    for page in year_pages(cfg, lo, hi):
        try:
            resp = requests.get(page, headers=HEADERS, timeout=20)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"    [ERR] {abbrev}: could not fetch {page}: {exc}")
            continue
        time.sleep(REQUEST_DELAY)

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/calendar/" not in href or not slug_re.search(href):
                continue
            m = DATE_IN_HREF.search(href)
            if not m:
                continue
            try:
                d = datetime.strptime(m.group(1), "%m%d%Y").date()
            except ValueError:
                continue
            if not (lo <= d <= hi):
                continue

            parent_text = a.parent.get_text(" ", strip=True) if a.parent else ""
            upper = parent_text.upper()
            if "CANCELLED" in upper or "CANCELED" in upper:
                if not quiet:
                    print(f"    [SKIP] {abbrev} {d.isoformat()} — cancelled")
                continue
            moved_to = _parse_resched(parent_text)
            if moved_to and moved_to != d:
                if not quiet:
                    print(f"    [SKIP] {abbrev} {d.isoformat()} — rescheduled to {moved_to.isoformat()}")
                continue

            full_url = urljoin(BASE_URL, href)
            key = (d.isoformat(), full_url)
            found.setdefault(key, {
                "committee": abbrev,
                "committee_full_name": (COMMITTEE_META.get(abbrev) or (abbrev,))[0],
                "date": d.isoformat(),
                "name": meeting_name(href),
                "url": full_url,
            })

    return list(found.values())


def local_docs(abbrev: str, iso_date: str) -> int:
    """Document count already downloaded for that meeting (0 if none/not yet)."""
    ddir = os.path.join(BASE_ROOT, abbrev, iso_date)
    if not os.path.isdir(ddir):
        return 0
    return sum(
        1 for f in os.listdir(ddir)
        if os.path.isfile(os.path.join(ddir, f))
        and not f.endswith(".tmp")
        and not f.lower().endswith((".zip", ".extracted"))
        and f != "_manifest.json"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the Meeting Timelines feed")
    ap.add_argument("--window", type=int, default=WINDOW_DAYS,
                    help=f"days before/after today to include (default {WINDOW_DAYS})")
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args()

    today = date.today()
    lo, hi = today - timedelta(days=args.window), today + timedelta(days=args.window)

    if not args.quiet:
        print(f"Meeting Timelines window: {lo} .. {hi}  ({len(COMMITTEES)} committees)")

    meetings: list[dict] = []
    for abbrev, cfg in COMMITTEES.items():
        rows = scrape_committee(abbrev, cfg, lo, hi, args.quiet)
        for r in rows:
            r["past"] = r["date"] < today.isoformat()
            r["doc_count"] = local_docs(abbrev, r["date"])
            r["on_file"] = r["doc_count"] > 0
        meetings.extend(rows)
        if not args.quiet:
            print(f"  {abbrev:<10} {len(rows):>3} meeting(s) in window")

    # Oldest first — the order the timeline renders top (past) to bottom (future).
    meetings.sort(key=lambda m: (m["date"], m["committee"], m["name"]))

    feed = {
        "generated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "window_days": args.window,
        "from": lo.isoformat(),
        "to": hi.isoformat(),
        "today": today.isoformat(),
        "meeting_count": len(meetings),
        "meetings": meetings,
    }
    os.makedirs(BASE_ROOT, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(feed, fh, ensure_ascii=False, indent=1)

    n_past = sum(1 for m in meetings if m["past"])
    print(f"Wrote {OUT_PATH} — {len(meetings)} meeting(s) "
          f"({n_past} past, {len(meetings) - n_past} upcoming), window {lo} .. {hi}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
