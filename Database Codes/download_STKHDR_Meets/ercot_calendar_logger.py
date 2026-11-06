#!/usr/bin/env python3
"""ERCOT calendar meeting logger.

Scrapes https://www.ercot.com/calendar, follows each meeting's detail page,
and writes one log file per meeting date listing every titled meeting with
its time, location, status, Webex link, Webex meeting number and password
(when ERCOT has posted them), teleconference line and webcast link.

ERCOT often adds the Webex number/password only a few days before a meeting,
so every run re-reads all upcoming meeting pages and rewrites the per-date
logs. Meetings still missing Webex details are flagged so the recorder (and a
later run) can pick them up.

Usage:
    py -3 "Database Codes/download_STKHDR_Meets/ercot_calendar_logger.py"
                                                    # default output folder (below)
    python ercot_calendar_logger.py --out D:/logs   # custom output folder
    python ercot_calendar_logger.py --days 14       # only meetings in next 14 days
    python ercot_calendar_logger.py --html-dir dump # also save raw HTML for debugging

Default output folder (Power.Talks convention, git-ignored):
    Documents Database/ERCOT.STKHDR.MEETS/_calendar_log/

Outputs (per meeting date):
    <out>/YYYY-MM-DD.log    human-readable summary
    <out>/YYYY-MM-DD.json   machine-readable list for the recording agent
    <out>/run_history.log   one line appended per run

Requires: Python 3.9+, requests, beautifulsoup4
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = PROJECT_ROOT / "Documents Database" / "ERCOT.STKHDR.MEETS" / "_calendar_log"

BASE_URL = "https://www.ercot.com"
CALENDAR_URL = f"{BASE_URL}/calendar"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# Detail pages look like /calendar/11062026-CIPWG-Meeting-_-Webex
DETAIL_HREF_RE = re.compile(r"/calendar/(\d{2})(\d{2})(\d{4})-[^\s\"'?#]+", re.I)

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
DATE_RE = re.compile(rf"\b({MONTHS})\.?\s+(\d{{1,2}}),\s*(\d{{4}})\b", re.I)
TIME_RE = re.compile(
    r"\b(\d{1,2}:\d{2}\s*[AP]\.?M\.?)(?:\s*(?:-|–|—|to)\s*(\d{1,2}:\d{2}\s*[AP]\.?M\.?))?",
    re.I,
)
# Webex meeting numbers are 9-11 digits, often grouped "2551 234 5678".
MEETING_NO_RE = re.compile(
    r"(?:meeting|event|webinar|session)\s*(?:number|num|no\.?|#|id)\s*(?:\(access code\))?"
    r"\s*[:\-]?\s*((?:\d[\s\-]?){9,11})",
    re.I,
)
ACCESS_CODE_RE = re.compile(r"access\s*code\s*[:\-]?\s*((?:\d[\s\-]?){6,11})", re.I)
PASSWORD_RE = re.compile(
    r"(?:meeting\s*|event\s*|webinar\s*)?(?:password|passcode|pass\s*code)\s*[:\-]?\s*([^\s,;]+)",
    re.I,
)
PHONE_RE = re.compile(r"(?:teleconference|call[\s-]*in|dial[\s-]*in|phone)\s*[:\-]?\s*(\+?1?[\s\-.]?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})", re.I)
LOCATION_HINT_RE = re.compile(r"\b(ERCOT Austin|ERCOT Taylor|Webex|Metropolis|Austin, TX|Taylor, TX)\b", re.I)


@dataclass
class Meeting:
    title: str
    url: str
    date: str  # YYYY-MM-DD
    time: str = ""
    end_time: str = ""
    group: str = ""
    group_verified: bool = False
    location: str = ""
    status: str = "Active"
    webex_url: str = ""
    webex_meeting_number: str = ""
    webex_password: str = ""
    webex_access_code: str = ""
    teleconference: str = ""
    webcast_url: str = ""
    ical_url: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def webex_details_complete(self) -> bool:
        return bool(self.webex_meeting_number and self.webex_password)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def digits_grouped(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    return " ".join(filter(None, [d[:-7], d[-7:-4], d[-4:]])) if len(d) >= 9 else d


# ------------------------------------------------------------------ group check
# The committee name comes from the title= attribute ERCOT puts on each
# calendar link, and ERCOT populates it unreliably: a workshop or Q&A session
# -- and sometimes the next committee meeting -- inherits the attribute of an
# earlier event. The 2026-11-06 "SB6 Large Load Curtailment" workshop and the
# 2026-11-09 PLWG meeting both arrived labelled "Critical Infrastructure
# Protection Working Group". The detail pages carry no committee of their own
# (every page embeds the same site-wide committee nav), so the attribute is the
# only source and has to be corroborated against the meeting title instead.
_GROUP_STOP = {"of", "and", "the", "for", "to", "a", "in", "on", "at"}

# "CANCELLED" / "canceled", as a word -- not "cancellation policy" and not the
# "cancel" inside some unrelated control label.
CANCELLED_PAT = re.compile(r"\bcancell?ed\b", re.IGNORECASE)


def title_acronyms(title: str) -> list[str]:
    """All-caps tokens in a meeting title -- its candidate committee acronym."""
    return [a for a in re.findall(r"\b([A-Z][A-Z0-9&]{1,9})\b", title or "")
            if a not in {"AND", "THE", "OF", "ERCOT"}]


def corroborates(acronym: str, phrase: str) -> bool:
    """True when `acronym` could be the acronym of `phrase`: either the phrase
    already starts with it, or its letters occur in order through the phrase
    (how "TXSETLP" sits inside "Texas Standard Electronic Transactions/Load
    Profiling Working Group"). Rejects a carried-over name, whose letters do
    not line up -- "PLWG" cannot be drawn from "Critical Infrastructure
    Protection Working Group"."""
    letters = re.sub(r"[^a-z]", "", (phrase or "").lower())
    want = re.sub(r"[^a-z]", "", (acronym or "").lower())
    if not want or not letters:
        return False
    if letters.startswith(want):
        return True
    i = 0
    for ch in want:
        i = letters.find(ch, i)
        if i < 0:
            return False
        i += 1
    return True


def verify_group(mt: "Meeting") -> None:
    """Keep the calendar's committee name only when the meeting title backs it
    up; otherwise drop it and keep what ERCOT claimed in the notes."""
    if not mt.group:
        return
    acronyms = title_acronyms(mt.title)
    if not acronyms:
        # Nothing in the title to check against: keep it, but say so.
        mt.notes.append(f"Group '{mt.group}' comes from the ERCOT calendar "
                        f"listing and could not be verified against the title")
        return
    if any(corroborates(a, mt.group) for a in acronyms):
        mt.group_verified = True
        return
    mt.notes.append(f"ERCOT calendar lists this under '{mt.group}', which does "
                    f"not match the meeting title; group omitted")
    mt.group = ""


class Fetcher:
    def __init__(self, delay: float = 1.0, retries: int = 3, html_dir: Path | None = None):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
        self.delay = delay
        self.retries = retries
        self.html_dir = html_dir
        if html_dir:
            html_dir.mkdir(parents=True, exist_ok=True)

    def get(self, url: str) -> str:
        last = None
        for attempt in range(1, self.retries + 1):
            try:
                r = self.s.get(url, timeout=30)
                r.raise_for_status()
                if self.html_dir:
                    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", url.split("ercot.com", 1)[-1]).strip("_") or "root"
                    (self.html_dir / f"{name[:150]}.html").write_text(r.text, encoding="utf-8")
                time.sleep(self.delay)
                return r.text
            except requests.RequestException as e:  # noqa: PERF203
                last = e
                logging.warning("GET %s failed (attempt %d/%d): %s", url, attempt, self.retries, e)
                time.sleep(2 ** attempt)
        raise RuntimeError(f"Could not fetch {url}: {last}")


# ---------------------------------------------------------------- calendar page
def _detail_urls(tag) -> set[str]:
    out = set()
    for a in tag.find_all("a", href=True):
        m = DETAIL_HREF_RE.search(urljoin(BASE_URL, a["href"]))
        if m:
            out.add(m.group(0))
    return out


def parse_calendar(html: str) -> list[Meeting]:
    """Return one Meeting stub per detail link on the calendar listing."""
    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, Meeting] = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(BASE_URL, a["href"])
        m = DETAIL_HREF_RE.search(href)
        title = clean(a.get_text(" "))
        if not m or not title or title.lower().startswith("add to"):
            continue
        url = href.split("#")[0]
        if url in seen:
            continue
        mm, dd, yyyy = m.groups()
        try:
            d = date(int(yyyy), int(mm), int(dd)).isoformat()
        except ValueError:
            continue
        mt = Meeting(title=title, url=url, date=d, group=clean(a.get("title", "")))
        # Look at the surrounding event block for time/location/status/iCal.
        # Climb while the ancestor still holds only this one event.
        block = a.parent or a
        for _ in range(4):
            parent = block.parent
            if parent is None or len(_detail_urls(parent)) > 1:
                break
            block = parent
        btext = clean(block.get_text(" "))
        if CANCELLED_PAT.search(btext):
            mt.status = "Cancelled"
        elif "reschedul" in btext.lower():
            mt.status = "Rescheduled"
        tm = TIME_RE.search(btext)
        if tm:
            mt.time, mt.end_time = clean(tm.group(1)), clean(tm.group(2) or "")
        loc = LOCATION_HINT_RE.search(btext)
        if loc:
            # Grab a short phrase around the hint, e.g. "ERCOT Austin & Webex".
            seg = re.search(r"((?:ERCOT\s+\w+\s*(?:&|and)?\s*)?Webex|ERCOT\s+\w+)", btext, re.I)
            mt.location = clean(seg.group(1)) if seg else loc.group(1)
        ical = block.find("a", href=re.compile(r"/ical/", re.I))
        if ical:
            mt.ical_url = urljoin(BASE_URL, ical["href"])
        seen[url] = mt
    return list(seen.values())


# ---------------------------------------------------------------- detail page
def parse_detail(html: str, mt: Meeting) -> Meeting:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find(id=re.compile("content|main", re.I)) or soup.body or soup
    for tag in main.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    # Every committee meeting page ends with a "Scheduled <X> Meetings" list of
    # that committee's other dates, and a past date in it may be marked
    # "(CANCELLED)". Reading it as part of this page's text cancelled live
    # meetings wholesale -- the 2026-11-05 ROS meeting was reported cancelled
    # because the list below it carries "Sep 03, 2026 - ROS Meeting
    # (CANCELLED)". It is also a second set of dates and times competing with
    # this meeting's own, so drop it before reading anything.
    for tag in main.find_all("section", id="otherMeetings"):
        tag.decompose()
    text = main.get_text("\n")
    flat = clean(text)

    h1 = main.find("h1")
    if h1 and clean(h1.get_text()):
        mt.title = clean(h1.get_text())

    dm = DATE_RE.search(flat)
    if dm:
        try:
            mt.date = datetime.strptime(
                f"{dm.group(1)[:3]} {dm.group(2)} {dm.group(3)}", "%b %d %Y"
            ).date().isoformat()
        except ValueError:
            pass
    if not mt.time:
        tm = TIME_RE.search(flat)
        if tm:
            mt.time, mt.end_time = clean(tm.group(1)), clean(tm.group(2) or "")

    if CANCELLED_PAT.search(flat):
        mt.status = "Cancelled"

    for a in main.find_all("a", href=True):
        href = a["href"]
        low = href.lower()
        if any(k in low for k in ("swagit", "webcast", "livestream")) and not mt.webcast_url:
            mt.webcast_url = urljoin(BASE_URL, href)
        elif "/ical/" in low and not mt.ical_url:
            mt.ical_url = urljoin(BASE_URL, href)
    if not mt.webcast_url and re.search(r"\bwebcast\b", flat, re.I):
        mt.notes.append("Page mentions a webcast")

    # Every Webex fact lives in one cell of the meeting's detail table:
    #
    #   <td class="webex">
    #     <a href="https://ercot.webex.com/ercot">WebEx Conference</a>
    #     Teleconference: 877-668-4493
    #     Meeting number: 2553 140 5933
    #     Meeting password: Xm#74
    #
    # so read them from that cell and nowhere else. This logger has already
    # shipped two bugs of exactly the opposite shape -- a past "(CANCELLED)"
    # in the page's own list of other meeting dates cancelling a live meeting,
    # and a neighbouring committee's name picked off an unrelated anchor --
    # and "password", "meeting number" and a phone number are all phrases that
    # recur further down a page in Comments and contact blurbs. The cell is
    # also the authority for the Webex address: the recorder opens the link
    # ERCOT publishes for this meeting rather than a constant of our own.
    cell = main.find("td", class_="webex")
    webex_text = clean(cell.get_text("\n")) if cell is not None else flat
    for a in (cell if cell is not None else main).find_all("a", href=True):
        if "webex.com" in a["href"].lower():
            mt.webex_url = urljoin(BASE_URL, a["href"])
            break

    if (m := MEETING_NO_RE.search(webex_text)):
        mt.webex_meeting_number = digits_grouped(m.group(1))
    if (m := ACCESS_CODE_RE.search(webex_text)):
        mt.webex_access_code = digits_grouped(m.group(1))
        if not mt.webex_meeting_number:
            mt.webex_meeting_number = mt.webex_access_code
    if (m := PASSWORD_RE.search(webex_text)):
        pw = m.group(1).strip(".")
        if pw.lower() not in {"required", "is", "protected", "n/a"}:
            mt.webex_password = pw
    # Webex join links sometimes carry the number: ...webex.com/...MTID=...  or ?MN=2551234567
    if not mt.webex_meeting_number and mt.webex_url:
        if (m := re.search(r"[?&](?:MN|meetingNumber|mn)=(\d{9,11})", mt.webex_url)):
            mt.webex_meeting_number = digits_grouped(m.group(1))
    if (m := PHONE_RE.search(webex_text)):
        mt.teleconference = clean(m.group(1))

    if not mt.location:
        for line in (clean(l) for l in text.splitlines()):
            if LOCATION_HINT_RE.search(line) and len(line) < 80:
                mt.location = line
                break

    if "contact" in flat.lower() and "for meeting details" in flat.lower():
        mt.notes.append("Page says to contact the chair for meeting details")
    return mt


# ---------------------------------------------------------------- output
def write_logs(meetings: list[Meeting], out: Path, run_ts: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    by_date: dict[str, list[Meeting]] = {}
    for mt in meetings:
        by_date.setdefault(mt.date, []).append(mt)
    written = []
    for d, items in sorted(by_date.items()):
        items.sort(key=lambda m: (_time_key(m.time), m.title))
        lines = [
            f"ERCOT meetings for {d} ({datetime.fromisoformat(d):%A})",
            f"Checked: {run_ts}  Source: {CALENDAR_URL}",
            f"Meetings: {len(items)}",
            "=" * 72,
        ]
        for i, m in enumerate(items, 1):
            when = m.time + (f" - {m.end_time}" if m.end_time else "")
            if m.webcast_url:
                rec = "ERCOT webcast (recorder can skip)"
            elif m.status == "Cancelled":
                rec = "cancelled"
            elif m.webex_details_complete:
                rec = "ready to record"
            elif m.webex_url:
                rec = "WAITING for Webex number/password"
            else:
                rec = "no Webex info"
            lines += [
                f"[{i}] {m.title}",
                f"    Time:            {when or 'n/a'} (Central)",
                f"    Status:          {m.status}",
                f"    Group:           {m.group or 'n/a'}"
                + ("" if not m.group or m.group_verified else "  (unverified)"),
                f"    Location:        {m.location or 'n/a'}",
                f"    Webex link:      {m.webex_url or 'n/a'}",
                f"    Meeting number:  {m.webex_meeting_number or 'not posted yet'}",
                f"    Password:        {m.webex_password or 'not posted yet'}",
            ]
            if m.webex_access_code and m.webex_access_code != m.webex_meeting_number:
                lines.append(f"    Access code:     {m.webex_access_code}")
            lines += [
                f"    Teleconference:  {m.teleconference or 'n/a'}",
                f"    Webcast:         {m.webcast_url or 'n/a'}",
                f"    Recording:       {rec}",
                f"    Page:            {m.url}",
            ]
            for n in m.notes:
                lines.append(f"    Note:            {n}")
            lines.append("-" * 72)
        p = out / f"{d}.log"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        payload = {
            "date": d,
            "checked": run_ts,
            "meetings": [asdict(m) | {"webex_details_complete": m.webex_details_complete} for m in items],
        }
        (out / f"{d}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written.append(p)
    return written


def _time_key(t: str) -> tuple:
    try:
        return (0, datetime.strptime(t.replace(".", "").upper().replace(" ", ""), "%I:%M%p").time())
    except ValueError:
        return (1, datetime.min.time())


# ---------------------------------------------------------------- main
def run(out: Path, days: int | None, delay: float, html_dir: Path | None, include_past: bool) -> int:
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f = Fetcher(delay=delay, html_dir=html_dir)
    logging.info("Fetching %s", CALENDAR_URL)
    try:
        stubs = parse_calendar(f.get(CALENDAR_URL))
    except RuntimeError as e:
        out.mkdir(parents=True, exist_ok=True)
        with (out / "run_history.log").open("a", encoding="utf-8") as h:
            h.write(f"{run_ts} ERROR {e}\n")
        logging.error("%s", e)
        return 1
    logging.info("Found %d meeting links on the calendar", len(stubs))
    today = date.today()
    keep = []
    for mt in stubs:
        d = date.fromisoformat(mt.date)
        if not include_past and d < today:
            continue
        if days is not None and d > today + timedelta(days=days):
            continue
        keep.append(mt)
    meetings, failures = [], 0
    for mt in keep:
        try:
            meetings.append(parse_detail(f.get(mt.url), mt))
        except Exception as e:  # keep going; log the stub so the date still appears
            failures += 1
            mt.notes.append(f"Detail page could not be read: {e}")
            meetings.append(mt)
            logging.error("Detail failed for %s: %s", mt.url, e)
        # After the detail page, so the check runs against its final title.
        verify_group(meetings[-1])
    written = write_logs(meetings, out, run_ts)
    ready = sum(m.webex_details_complete for m in meetings)
    summary = (
        f"{run_ts} calendar_links={len(stubs)} logged={len(meetings)} dates={len(written)} "
        f"webex_ready={ready} detail_failures={failures}"
    )
    with (out / "run_history.log").open("a", encoding="utf-8") as h:
        h.write(summary + "\n")
    print(summary, flush=True)
    return 0 if stubs else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--days", type=int, default=None, help="only log meetings within N days from today")
    ap.add_argument("--include-past", action="store_true", help="also log meetings dated before today")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (be polite)")
    ap.add_argument("--html-dir", type=Path, default=None, help="save raw HTML here for debugging")
    ap.add_argument("--quiet", action="store_true", help="only print warnings and the run summary")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return run(a.out, a.days, a.delay, a.html_dir, a.include_past)


if __name__ == "__main__":
    sys.exit(main())
