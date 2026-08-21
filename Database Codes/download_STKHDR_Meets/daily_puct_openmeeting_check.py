#!/usr/bin/env python3
"""
Daily PUCT open-meeting audio grabber (scheduled task target).

AdminMonitor posts each PUCT open meeting as an on-demand video a few hours
after it ends. This runs daily, scrapes the PUCT open-meeting listing, and for
every meeting within a recent window whose MP3 we don't already have, downloads
the audio. Meetings not yet posted are skipped quietly and retried the next day,
so the exact run time doesn't matter (the window makes it self-healing).

For each meeting it grabs the audio MP3 and the FINAL agenda .docx (the archived
status_id=3 agenda linked on the meeting page = the agenda as of the meeting's
END, not the live start-time one). Reuses the helpers in download_puct_openmeeting.py.

Registered as Windows task "PUCT_OpenMeeting_Daily_Download" (see README/notes).
Writes its own log to Documents Database/ERCOT.STKHDR.MEETS/PUCT/daily_check.log
because Task Scheduler does not capture stdout.
"""

import argparse
import datetime
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import download_puct_openmeeting as D   # BASE, UA, OUT_DIR, find_master_m3u8, ffmpeg_pull

WINDOW_DAYS = 21   # look back this far; re-tries meetings whose VOD posts late
LOG_FILE = os.path.join(D.OUT_DIR, "daily_check.log")


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    try:
        os.makedirs(D.OUT_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def list_meeting_dates():
    """Return sorted YYYYMMDD codes from the AdminMonitor PUCT listing."""
    r = requests.get(D.BASE + "/", headers={"User-Agent": D.UA}, timeout=60)
    r.raise_for_status()
    return sorted(set(re.findall(r"/tx/puct/open_meeting/(\d{8})/", r.text)))


def main():
    ap = argparse.ArgumentParser(description="Daily PUCT open-meeting audio grabber.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be downloaded, but download nothing")
    args = ap.parse_args()

    today = datetime.date.today()
    lo = today - datetime.timedelta(days=WINDOW_DAYS)
    try:
        dates = list_meeting_dates()
    except requests.RequestException as e:
        log(f"ERROR listing meetings: {e}")
        sys.exit(1)

    log(f"listing OK: {len(dates)} meetings; window {lo}..{today}"
        f"{' [DRY RUN]' if args.dry_run else ''}")
    got = 0
    for d in dates:
        try:
            day = datetime.datetime.strptime(d, "%Y%m%d").date()
        except ValueError:
            continue
        if day < lo or day > today:
            continue   # only recent meetings that have already happened

        mp3 = os.path.join(D.OUT_DIR, f"PUCT_OpenMeeting_{d}.mp3")
        agenda = os.path.join(D.OUT_DIR, f"PUCT_Agenda_{d}.docx")
        need_audio = not os.path.exists(mp3)
        need_agenda = not os.path.exists(agenda)
        if not need_audio and not need_agenda:
            continue   # already have both audio and final agenda

        # One page fetch feeds both the video URL and the (final) agenda URL.
        try:
            html = D.get_meeting_html(d)
        except RuntimeError as e:
            log(f"{d}: page error, will retry tomorrow ({e})")
            continue
        if not html:
            continue   # meeting page not up

        # --- audio ---
        if need_audio:
            m3u8 = D.master_m3u8_from_html(html)
            if not m3u8:
                log(f"{d}: VOD not posted yet, will retry tomorrow")
            elif args.dry_run:
                log(f"{d}: WOULD download audio -> {os.path.basename(mp3)}")
                got += 1
            else:
                log(f"{d}: downloading audio -> {os.path.basename(mp3)}")
                try:
                    D.ffmpeg_pull(m3u8, mp3, audio_only=True)
                    log(f"{d}: audio done ({os.path.getsize(mp3)/(1024*1024):.1f} MB)")
                    got += 1
                except RuntimeError as e:
                    log(f"{d}: audio failed, will retry tomorrow ({e})")

        # --- final (archived) agenda ---
        if need_agenda:
            agenda_url = D.agenda_url_from_html(html)
            if not agenda_url:
                log(f"{d}: no agenda on page yet, will retry tomorrow")
            elif args.dry_run:
                log(f"{d}: WOULD fetch final agenda -> {os.path.basename(agenda)}")
            else:
                try:
                    D.fetch_agenda_docx(agenda_url, agenda)
                    log(f"{d}: agenda done -> {os.path.basename(agenda)}")
                except RuntimeError as e:
                    log(f"{d}: agenda failed, will retry tomorrow ({e})")

    log(f"daily check complete: {got} new audio download(s)")


if __name__ == "__main__":
    main()
