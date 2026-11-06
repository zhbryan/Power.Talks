#!/usr/bin/env python3
"""ERCOT Webex meeting audio recorder.

Joins one ERCOT meeting as a muted, camera-off guest through the Webex **web**
app in a Playwright-driven Chromium window, records the meeting audio inside
the page, and writes an .mp3 into that meeting's dated folder:

    Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD>/
        2026-11-05_ROS_ROS-Meeting.mp3
        2026-11-05_ROS_ROS-Meeting.recording.log

Recording happens in the browser, not on the sound card: an init script wraps
RTCPeerConnection so every incoming audio track is routed into one
AudioContext destination, and a MediaRecorder on that destination streams
Opus chunks back to Python, which appends them to disk as they arrive. That
captures only the meeting (no system sounds), survives you using the PC, and
keeps at most a few seconds of audio at risk if anything crashes. Webex's own
Record button is a host privilege and is not available to a guest.

Credentials are re-scraped from the meeting's own ERCOT page at launch, since
ERCOT posts the Webex number and password close to the meeting date -- the
nightly calendar log is often still empty when the job is scheduled.

The meeting is skipped, with the reason written to the log, when it is
cancelled, when ERCOT webcasts it (those are already archived officially), or
when no Webex number/password has been posted by start time.

Usage:
    python webex_recorder.py --from-log --date 2026-11-05 --title "ROS Meeting"
    python webex_recorder.py --meeting-number "2553 140 5933" --password "Xm#74" \
                             --date 2026-11-05 --title "ROS Meeting" --committee ROS
    python webex_recorder.py --self-test        # prove the capture path locally
    python webex_recorder.py --from-log --date 2026-11-05 --title "ROS Meeting" --plan

Requires: playwright (+ `playwright install chromium`), ffmpeg on PATH,
requests, beautifulsoup4. Must run in a logged-on desktop session: the browser
is headed on purpose, because a headless Chromium gets no audio from Webex.
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
MEETS_ROOT = PROJECT_ROOT / "Documents Database" / "ERCOT.STKHDR.MEETS"
CALENDAR_LOG = MEETS_ROOT / "_calendar_log"
UNFILED = "_unfiled"

WEBEX_SITE = "https://ercot.webex.com/ercot"
DEFAULT_DISPLAY_NAME = "Bryan Zhang (listen only)"
DEFAULT_EMAIL = "chunliang.zhang@gmail.com"

# Stop when no audio has arrived for this long, or at the hard cap, whichever
# comes first. The doc's end conditions: meeting ended, silence, hard cap.
SILENCE_STOP_MIN = 20
HARD_CAP_MIN = 300
CHUNK_MS = 5000

sys.path.insert(0, str(HERE))


# ─── IN-PAGE RECORDER ────────────────────────────────────────────────────────
# Installed with add_init_script, so it is in place before Webex's own code
# runs and cannot miss a peer connection. A Proxy is used rather than a
# function wrapper so RTCPeerConnection keeps its prototype and statics.
INIT_SCRIPT = r"""
(() => {
  if (window.__ptInstalled) return;
  window.__ptInstalled = true;
  window.__ptTracks = 0;
  window.__ptBytes = 0;
  window.__ptEnded = false;

  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  const ctx = new AC();
  const dest = ctx.createMediaStreamDestination();
  window.__ptCtx = ctx;
  window.__ptDest = dest;

  // A remote WebRTC track feeds a Web Audio graph only while it is ALSO sunk
  // to a media element that is playing: without the element below, the graph
  // receives digital silence even though the track is live and unmuted (the
  // recorder captured a 6-second file of -91 dB before this was added). The
  // element stays muted, so nothing reaches the speakers; the audio we keep
  // comes off the graph. The references are held so neither is collected.
  window.__ptSinks = [];
  window.__ptSources = [];
  const attach = (track) => {
    try {
      if (!track || track.kind !== "audio") return;
      const ms = new MediaStream([track]);
      const el = new Audio();
      el.srcObject = ms;
      el.muted = true;
      el.autoplay = true;
      el.play().catch(() => {});
      window.__ptSinks.push(el);
      const src = ctx.createMediaStreamSource(ms);
      src.connect(dest);
      window.__ptSources.push(src);
      window.__ptTracks += 1;
    } catch (e) { /* a track that cannot be sourced is simply not recorded */ }
  };

  const Orig = window.RTCPeerConnection;
  if (Orig) {
    window.RTCPeerConnection = new Proxy(Orig, {
      construct(target, args) {
        const pc = new target(...args);
        pc.addEventListener("track", (e) => attach(e.track));
        return pc;
      },
    });
  }

  window.__ptStart = async () => {
    if (window.__ptRec) return true;
    try { if (ctx.state === "suspended") await ctx.resume(); } catch (e) {}
    const rec = new MediaRecorder(dest.stream, {
      mimeType: "audio/webm;codecs=opus",
      audioBitsPerSecond: 64000,
    });
    rec.ondataavailable = async (e) => {
      if (!e.data || !e.data.size) return;
      const bytes = new Uint8Array(await e.data.arrayBuffer());
      let s = "";
      const STEP = 0x8000;
      for (let i = 0; i < bytes.length; i += STEP) {
        s += String.fromCharCode.apply(null, bytes.subarray(i, i + STEP));
      }
      window.__ptBytes += bytes.length;
      try { await window.__ptChunk(btoa(s)); } catch (err) {}
    };
    rec.start(__CHUNK_MS__);
    window.__ptRec = rec;
    return true;
  };

  window.__ptStop = () => {
    try { if (window.__ptRec && window.__ptRec.state !== "inactive") window.__ptRec.stop(); }
    catch (e) {}
    return window.__ptBytes;
  };

  window.__ptStats = () => ({
    tracks: window.__ptTracks,
    bytes: window.__ptBytes,
    recording: !!(window.__ptRec && window.__ptRec.state === "recording"),
  });
})();
"""

ENDED_PATTERNS = [
    "meeting has ended", "this meeting has ended", "the meeting is over",
    "you have been removed", "host has ended", "meeting ended",
]


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-")
    return re.sub(r"-{2,}", "-", s)[:60] or "Meeting"


def known_committees() -> set[str]:
    """Acronyms this project files meetings under. Delegated to
    committee_registry, which derives the live set from ERCOT's calendar
    rather than the downloader's hand-maintained dict -- a working group
    ERCOT stood up last month is filed under its own folder instead of
    `_unfiled`."""
    try:
        import committee_registry
        return committee_registry.known_committees()
    except Exception:
        found = set()
        if MEETS_ROOT.is_dir():
            found |= {p.name for p in MEETS_ROOT.iterdir()
                      if p.is_dir() and not p.name.startswith("_")}
        return found


def committee_for(title: str, known: set[str] | None = None) -> str:
    """The committee folder a meeting belongs in, from its title's acronym."""
    known = known if known is not None else known_committees()
    for token in re.findall(r"\b([A-Z][A-Z0-9]{1,9})\b", title or ""):
        if token in known:
            return token
    return UNFILED


def meeting_dir(date_str: str, committee: str) -> Path:
    return MEETS_ROOT / committee / date_str


def load_from_log(date_str: str, title: str) -> dict | None:
    """The meeting as the calendar logger last recorded it."""
    path = CALENDAR_LOG / f"{date_str}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    wanted = (title or "").strip().lower()
    for m in data.get("meetings", []):
        if m.get("title", "").strip().lower() == wanted:
            return m
    for m in data.get("meetings", []):      # fall back to a prefix match
        if wanted and m.get("title", "").strip().lower().startswith(wanted[:12]):
            return m
    return None


def refresh_from_page(meeting: dict) -> dict:
    """Re-scrape the meeting's ERCOT page for credentials posted since the
    nightly run. Returns the meeting unchanged if the page cannot be read."""
    url = meeting.get("url")
    if not url:
        return meeting
    try:
        import ercot_calendar_logger as cl
        fetcher = cl.Fetcher(delay=0.0)
        stub = cl.Meeting(title=meeting.get("title", ""), url=url,
                          date=meeting.get("date", ""),
                          time=meeting.get("time", ""),
                          group=meeting.get("group", ""),
                          location=meeting.get("location", ""),
                          status=meeting.get("status", "Active"))
        fresh = cl.parse_detail(fetcher.get(url), stub)
        cl.verify_group(fresh)
        from dataclasses import asdict
        out = asdict(fresh)
        out["webex_details_complete"] = fresh.webex_details_complete
        return out
    except Exception as e:
        logging.warning("Could not re-read %s: %s", url, e)
        return meeting


def skip_reason(meeting: dict) -> str | None:
    if str(meeting.get("status", "")).lower().startswith("cancel"):
        return "meeting is cancelled"
    if meeting.get("webcast_url"):
        return f"ERCOT webcasts this meeting ({meeting['webcast_url']}); it is archived officially"
    if not (meeting.get("webex_meeting_number") and meeting.get("webex_password")):
        return "no Webex meeting number/password posted"
    return None


# ─── THE WEBEX JOIN SEQUENCE ─────────────────────────────────────────────────
# Every selector below was read off the live site, not guessed. The first real
# run (ROS, 2026-11-05) died on step 1: the join box carries no placeholder and
# its aria-label is "Enter meeting information", so every selector that looked
# for "meeting number" or a placeholder missed it. The steps after it were
# wrong too and would have failed in turn -- the password gate's submit button
# is "OK" rather than "Join", "Join Meeting" is a <div> and not a <button>, and
# the name box is a web component inside an iframe from web.webex.com with a
# generated id. The shape of the flow is:
#
#   ERCOT's "WebEx Conference" link -> #ipt-joinmeeting + Enter
#     -> #meetingInfoPassword + "OK"
#     -> the meeting-info page, which publishes the real .../j.php?MTID=... link
#     -> "Join from this browser"  (#broadcom-center-right)
#     -> name + mute + #join-button, inside the web.webex.com iframe
JOIN_BOX_SELECTORS = (
    "#ipt-joinmeeting",
    'input[aria-label*="Enter meeting" i]',
    'input[placeholder*="meeting number" i]',
    'input[aria-label*="meeting number" i]',
    "#join-meeting-input",
    'input[type="search"]',
)
PASSWORD_GATE_SELECTORS = ("#meetingInfoPassword", 'input[type="password"]')
BROWSER_JOIN_SELECTORS = (
    "#broadcom-center-right",
    'text="Join from this browser"',
    'text="Join from your browser"',
    'text="Use web app"',
)
MTID_RE = re.compile(r"https://[^\s\"'<>|]*j\.php\?MTID=[A-Za-z0-9]+")


def dismiss_cookies(page) -> None:
    """Webex's cookie banner covers the bottom of every page and eats clicks
    aimed at what is behind it."""
    for name in ("Accept", "Allow all", "Reject"):
        try:
            btn = page.get_by_role("button", name=name, exact=True).first
            if btn.count():
                btn.click(timeout=4000)
                return
        except Exception:
            continue


def first_visible(scope, selectors, timeout: int = 8000):
    for sel in selectors:
        try:
            loc = scope.locator(sel).first
            if loc.count():
                loc.wait_for(state="visible", timeout=timeout)
                return loc
        except Exception:
            continue
    return None


def click_first(scope, labels) -> bool:
    """Click the first of `labels` that exists anywhere in the page or its
    frames, then stop. The version this replaces walked every label in turn,
    so a screen carrying both "Next" and "Join" received both clicks."""
    frames = [scope] + list(getattr(scope, "frames", None) or [])
    for label in labels:
        for frame in frames:
            try:
                btn = frame.get_by_role(
                    "button", name=re.compile(f"^{re.escape(label)}$", re.I)).first
                if btn.count():
                    btn.click(timeout=10_000)
                    return True
            except Exception:
                continue
    return False


def set_av_off(scope) -> None:
    """Mute the microphone and keep the camera off.

    Webex states the *current* state in the aria-label ("Microphone is
    currently unmuted - click to mute"), so read it instead of clicking
    blindly: a blind click on an already-muted mic opens it into the meeting.
    """
    try:
        buttons = scope.get_by_role("button")
        count = min(buttons.count(), 30)
    except Exception:
        return
    for i in range(count):
        button = buttons.nth(i)
        try:
            label = (button.get_attribute("aria-label") or "").lower()
        except Exception:
            continue
        if "currently unmuted" in label:
            want = "mute the microphone"
        elif "video is currently enabled" in label:
            want = "stop the camera"
        else:
            continue
        try:
            button.click(timeout=5000)
            logging.info("Clicked to %s", want)
        except Exception as e:
            logging.warning("Could not %s: %s", want, e)


def webex_app_frame(page):
    """The join screen is served in an iframe from web.webex.com."""
    for frame in page.frames:
        if "web.webex.com" in (frame.url or ""):
            return frame
    return page


def describe_page(page) -> str:
    """What is actually on screen, for the log when a step finds nothing. The
    first failure cost a whole meeting because the log said only that a
    selector had missed."""
    try:
        return json.dumps(page.evaluate(
            "() => ({url: location.href,"
            " inputs: [...document.querySelectorAll('input')]"
            "   .filter(e => e.type !== 'hidden')"
            "   .map(e => [e.id, e.type, e.placeholder,"
            "              e.getAttribute('aria-label')]),"
            " clickable: [...document.querySelectorAll('button,a,[role=button]')]"
            "   .filter(e => e.offsetWidth || e.offsetHeight)"
            "   .map(e => (e.textContent || '').trim().slice(0, 40))"
            "   .filter(Boolean).slice(0, 25)})"), ensure_ascii=False)[:1600]
    except Exception as e:
        return f"(could not read the page: {e})"


# ─── JOIN + RECORD ───────────────────────────────────────────────────────────
def record(meeting: dict, out_dir: Path, base: str, display_name: str,
           email: str, hard_cap_min: int, keep_webm: bool,
           shots_dir: Path) -> Path | None:
    from playwright.sync_api import sync_playwright

    webm = out_dir / f"{base}.webm"
    mp3 = out_dir / f"{base}.mp3"
    number = re.sub(r"\D", "", meeting["webex_meeting_number"])
    password = meeting["webex_password"]

    fh = webm.open("wb")
    state = {"bytes": 0, "last": time.time()}

    def on_chunk(b64: str) -> None:
        raw = base64.b64decode(b64)
        fh.write(raw)
        fh.flush()
        state["bytes"] += len(raw)
        state["last"] = time.time()

    shot_n = {"i": 0}

    def shot(page, tag: str) -> None:
        shot_n["i"] += 1
        try:
            page.screenshot(path=str(shots_dir / f"{shot_n['i']:02d}-{tag}.png"))
        except Exception:
            pass

    started = time.time()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, args=[
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ])
            ctx = browser.new_context(permissions=["microphone"])
            ctx.grant_permissions(["microphone"], origin="https://ercot.webex.com")
            page = ctx.new_page()
            page.expose_function("__ptChunk", on_chunk)
            page.add_init_script(INIT_SCRIPT.replace("__CHUNK_MS__", str(CHUNK_MS)))

            # ERCOT's meeting page links its own "WebEx Conference" address;
            # use that rather than this project's idea of the site.
            site = meeting.get("webex_url") or WEBEX_SITE
            logging.info("Opening %s", site)
            page.goto(site, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(6000)
            dismiss_cookies(page)
            shot(page, "site")

            # 1. Meeting number.
            box = first_visible(page, JOIN_BOX_SELECTORS, timeout=20_000)
            if box is None:
                logging.error("Join box not found. Page: %s", describe_page(page))
                raise RuntimeError("could not find the meeting-number box on the Webex site")
            box.fill(number, timeout=20_000)
            box.press("Enter")
            page.wait_for_timeout(10_000)
            shot(page, "number")

            # 2. The password gate on the meeting-info page.
            gate = first_visible(page, PASSWORD_GATE_SELECTORS, timeout=15_000)
            if gate is None:
                logging.info("No password gate shown; continuing")
            else:
                gate.fill(password, timeout=10_000)
                if not click_first(page, ("OK", "Continue", "Submit", "Next")):
                    gate.press("Enter")
                page.wait_for_timeout(10_000)
            shot(page, "meeting-info")

            # 3. That page publishes the meeting's real join link. Following it
            #    beats clicking "Join Meeting", which is a <div>, and it lands
            #    directly on the browser/desktop choice.
            link = page.evaluate(
                "() => { const a = [...document.querySelectorAll('a')]"
                "  .find(x => (x.href || '').includes('j.php?MTID='));"
                "  return a ? a.href : ''; }")
            if not link:
                found = MTID_RE.search(page.inner_text("body", timeout=5000) or "")
                link = found.group(0) if found else ""
            if link:
                logging.info("Join link: %s", link)
                page.goto(link, wait_until="domcontentloaded", timeout=90_000)
                page.wait_for_timeout(12_000)
            elif not click_first(page, ("Join Meeting", "Join meeting")):
                logging.error("Nothing to join with. Page: %s", describe_page(page))
                raise RuntimeError("the meeting-info page offered no way to join")
            dismiss_cookies(page)
            shot(page, "join-page")

            # 4. The browser client, not the desktop app.
            webapp = first_visible(page, BROWSER_JOIN_SELECTORS, timeout=25_000)
            if webapp is None:
                logging.error("No browser-client choice. Page: %s", describe_page(page))
                raise RuntimeError("Webex did not offer to join from this browser")
            webapp.click(timeout=15_000)
            page.wait_for_timeout(20_000)
            shot(page, "browser-client")

            # 5. Name, mute, join -- inside the web.webex.com iframe, whose
            #    fields are web components with generated ids, so go by role.
            app = webex_app_frame(page)
            try:
                app.get_by_role("textbox").first.fill(display_name, timeout=20_000)
            except Exception as e:
                logging.warning("Could not type the display name: %s", e)
            for sel in ('input[type="email"]', 'input[placeholder*="email" i]',
                        'input[aria-label*="email" i]'):
                try:
                    loc = app.locator(sel).first
                    if loc.count():
                        loc.fill(email, timeout=8000)
                        break
                except Exception:
                    continue
            set_av_off(app)
            shot(page, "identity")

            joined = False
            try:
                button = app.locator("#join-button").first
                if button.count():
                    button.click(timeout=15_000)
                    joined = True
            except Exception as e:
                logging.warning("#join-button did not take the click: %s", e)
            if not joined:
                joined = click_first(app, ("Join meeting", "Join now", "Join"))
            if not joined:
                logging.error("No join button. Page: %s", describe_page(page))
                raise RuntimeError("could not press Join on the Webex join screen")
            page.wait_for_timeout(20_000)
            shot(page, "joined")

            # Once inside, confirm we are muted and dark.
            set_av_off(webex_app_frame(page))

            page.evaluate("window.__ptStart && window.__ptStart()")
            logging.info("Recording started -> %s", webm.name)
            state["last"] = time.time()

            cap = started + hard_cap_min * 60
            last_log = 0.0
            while True:
                page.wait_for_timeout(5000)
                now = time.time()
                try:
                    stats = page.evaluate("window.__ptStats ? window.__ptStats() : null") or {}
                except Exception:
                    stats = {}
                if now - last_log > 60:
                    last_log = now
                    logging.info("tracks=%s bytes=%s elapsed=%dm",
                                 stats.get("tracks"), state["bytes"],
                                 (now - started) / 60)
                if now > cap:
                    logging.info("Hard cap of %d min reached", hard_cap_min)
                    break
                if state["bytes"] and now - state["last"] > SILENCE_STOP_MIN * 60:
                    logging.info("No audio for %d min; stopping", SILENCE_STOP_MIN)
                    break
                try:
                    body = (page.inner_text("body", timeout=5000) or "").lower()
                except Exception:
                    body = ""
                if any(p in body for p in ENDED_PATTERNS):
                    logging.info("Page reports the meeting ended")
                    break
                if page.is_closed():
                    break

            try:
                page.evaluate("window.__ptStop && window.__ptStop()")
                page.wait_for_timeout(CHUNK_MS + 1500)
            except Exception:
                pass
            shot(page, "end")
            ctx.close()
            browser.close()
    finally:
        fh.close()

    if not state["bytes"]:
        logging.error("No audio captured; leaving %s for inspection", webm.name)
        return None

    logging.info("Captured %.1f MB; converting to mp3", state["bytes"] / 1e6)
    cmd = ["ffmpeg", "-y", "-i", str(webm), "-ac", "1", "-b:a", "64k", str(mp3)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not mp3.exists():
        logging.error("ffmpeg failed: %s", (proc.stderr or "")[-400:])
        return None
    if not keep_webm:
        try:
            webm.unlink()
        except OSError:
            pass
    return mp3


# ─── SELF TEST ───────────────────────────────────────────────────────────────
SELF_TEST_PAGE = r"""
<!doctype html><meta charset="utf-8"><title>pt self test</title><body>
<script>
// Two peer connections wired to each other locally: one sends a synthesised
// tone, the other receives it. The init script's hook should see the incoming
// track exactly as it sees a Webex participant's.
(async () => {
  const ctx = new AudioContext();
  const osc = ctx.createOscillator(); osc.frequency.value = 440;
  const dst = ctx.createMediaStreamDestination(); osc.connect(dst); osc.start();
  const a = new RTCPeerConnection(), b = new RTCPeerConnection();
  a.onicecandidate = e => e.candidate && b.addIceCandidate(e.candidate);
  b.onicecandidate = e => e.candidate && a.addIceCandidate(e.candidate);
  dst.stream.getAudioTracks().forEach(t => a.addTrack(t, dst.stream));
  const offer = await a.createOffer(); await a.setLocalDescription(offer);
  await b.setRemoteDescription(offer);
  const ans = await b.createAnswer(); await b.setLocalDescription(ans);
  await a.setRemoteDescription(ans);
  document.title = "pt self test ready";
})();
</script></body>
"""


def self_test(out_dir: Path) -> int:
    """Prove the capture path end to end without Webex: a local WebRTC
    loopback carrying a 440 Hz tone, recorded through the same init script and
    converted with the same ffmpeg call."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    webm = out_dir / "selftest.webm"
    mp3 = out_dir / "selftest.mp3"
    fh = webm.open("wb")
    got = {"bytes": 0}

    def on_chunk(b64: str) -> None:
        raw = base64.b64decode(b64)
        fh.write(raw)
        got["bytes"] += len(raw)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, args=[
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ])
            page = browser.new_context().new_page()
            page.expose_function("__ptChunk", on_chunk)
            page.add_init_script(INIT_SCRIPT.replace("__CHUNK_MS__", "1000"))
            # The page must be fetched, not injected: an init script runs on a
            # new document, and set_content writes into the current one. Served
            # over localhost so the page is a secure context for WebRTC.
            page.route("**/__pt_selftest", lambda route: route.fulfill(
                status=200, content_type="text/html; charset=utf-8",
                body=SELF_TEST_PAGE))
            page.goto("http://localhost/__pt_selftest", wait_until="load")
            page.wait_for_timeout(3000)
            stats = page.evaluate("window.__ptStats()")
            print(f"  hook installed, incoming audio tracks seen: {stats['tracks']}")
            page.evaluate("window.__ptStart()")
            page.wait_for_timeout(6000)
            page.evaluate("window.__ptStop()")
            page.wait_for_timeout(1500)
            stats = page.evaluate("window.__ptStats()")
            browser.close()
    finally:
        fh.close()

    print(f"  bytes streamed to Python: {got['bytes']}")
    if not got["bytes"]:
        print("  FAIL: no audio reached Python")
        return 1
    proc = subprocess.run(["ffmpeg", "-y", "-i", str(webm), "-ac", "1",
                           "-b:a", "64k", str(mp3)], capture_output=True, text=True)
    if proc.returncode != 0 or not mp3.exists():
        print("  FAIL: ffmpeg could not convert the capture")
        print((proc.stderr or "")[-400:])
        return 1
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", str(mp3)],
                         capture_output=True, text=True).stdout.strip()
    print(f"  mp3 written: {mp3} ({mp3.stat().st_size} bytes, {dur or '?'}s)")

    # A file of the right length proves nothing: the first working version of
    # this recorder produced 6 seconds of digital silence. Measure the level.
    det = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp3),
                          "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", det)
    mean = float(m.group(1)) if m else -999.0
    print(f"  mean volume: {mean:.1f} dB")
    if mean < -60:
        print("  FAIL: the capture is silent -- audio is not reaching the graph")
        return 1
    print("  PASS: hook -> media-element sink -> MediaRecorder -> Python -> audible mp3")
    return 0


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="meeting date, YYYY-MM-DD")
    ap.add_argument("--title", help="meeting title as the calendar log has it")
    ap.add_argument("--from-log", action="store_true",
                    help="take the meeting out of _calendar_log/<date>.json")
    ap.add_argument("--no-refresh", action="store_true",
                    help="do not re-scrape the ERCOT page for late credentials")
    ap.add_argument("--meeting-number")
    ap.add_argument("--password")
    ap.add_argument("--committee", help="override the committee folder")
    ap.add_argument("--out", help="override the output folder entirely")
    ap.add_argument("--display-name", default=DEFAULT_DISPLAY_NAME)
    ap.add_argument("--email", default=DEFAULT_EMAIL)
    ap.add_argument("--max-minutes", type=int, default=HARD_CAP_MIN)
    ap.add_argument("--keep-webm", action="store_true")
    ap.add_argument("--plan", action="store_true",
                    help="resolve everything and report, but do not join")
    ap.add_argument("--self-test", action="store_true",
                    help="verify the capture path locally, without Webex")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.self_test:
        return self_test(Path(args.out) if args.out
                         else PROJECT_ROOT / "Database Codes" / "logs" / "webex_selftest")

    if not args.date or not args.title:
        ap.error("--date and --title are required (or use --self-test)")

    meeting = load_from_log(args.date, args.title) if args.from_log else None
    if meeting is None:
        meeting = {"title": args.title, "date": args.date, "status": "Active",
                   "url": "", "group": "", "location": "", "time": ""}
    if args.meeting_number:
        meeting["webex_meeting_number"] = args.meeting_number
    if args.password:
        meeting["webex_password"] = args.password
    if not args.no_refresh and meeting.get("url"):
        meeting = refresh_from_page(meeting)
        if args.meeting_number:
            meeting["webex_meeting_number"] = args.meeting_number
        if args.password:
            meeting["webex_password"] = args.password

    committee = args.committee or committee_for(meeting.get("title", args.title))
    out_dir = Path(args.out) if args.out else meeting_dir(args.date, committee)
    base = f"{args.date}_{committee}_{slugify(meeting.get('title', args.title))}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{base}.recording.log"

    fileh = logging.FileHandler(log_path, encoding="utf-8")
    fileh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fileh)

    logging.info("Meeting : %s (%s %s)", meeting.get("title"), args.date,
                 meeting.get("time") or "time unknown")
    logging.info("Folder  : %s", out_dir)
    # The password is printed, not masked: ERCOT publishes it on the public
    # meeting page, and "password: set" told us nothing when the first run
    # failed -- there was no way to tell a mis-read password from a mis-read
    # page without re-scraping by hand.
    logging.info("Status  : %s   Webex number: %s   password: %s",
                 meeting.get("status"),
                 meeting.get("webex_meeting_number") or "not posted",
                 meeting.get("webex_password") or "not posted")
    logging.info("Webex   : %s", meeting.get("webex_url") or WEBEX_SITE)

    reason = skip_reason(meeting)
    if reason:
        logging.warning("SKIPPED: %s", reason)
        return 0

    if args.plan:
        logging.info("--plan: would join %s as '%s' and write %s",
                     meeting.get("webex_url") or WEBEX_SITE,
                     args.display_name, out_dir / f"{base}.mp3")
        return 0

    shots = out_dir / f"{base}.screenshots"
    shots.mkdir(exist_ok=True)
    try:
        mp3 = record(meeting, out_dir, base, args.display_name, args.email,
                     args.max_minutes, args.keep_webm, shots)
    except Exception as e:
        logging.exception("Recording failed: %s", e)
        return 1
    if not mp3:
        return 1
    logging.info("DONE: %s (%.1f MB)", mp3, mp3.stat().st_size / 1e6)
    return 0


if __name__ == "__main__":
    sys.exit(main())
