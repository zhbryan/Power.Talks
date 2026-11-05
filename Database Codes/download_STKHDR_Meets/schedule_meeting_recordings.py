#!/usr/bin/env python3
"""Schedule one Webex recording job per upcoming ERCOT meeting.

Reads the calendar logger's output (ERCOT.STKHDR.MEETS/_calendar_log/*.json)
and registers a Windows scheduled task per meeting that runs webex_recorder.py
a few minutes before it starts. Each recording lands in that meeting's dated
folder under ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD>/.

The calendar log is a moving target -- ERCOT posts Webex numbers and passwords
close to the date, adds meetings and cancels others -- so this is meant to run
every day after the logger. It is idempotent: tasks are rewritten (/f) on each
run, meetings that have been cancelled or whose pages now show a webcast have
their tasks removed, and tasks whose meeting has passed are pruned. Meetings
with no credentials yet are still scheduled, because the recorder re-scrapes
the meeting page when it starts and will skip cleanly if they never appear.

Tasks are named  PowerTalks_Rec_<YYYY-MM-DD>_<COMMITTEE>_<slug>  so they are
easy to find, audit and delete as a group.

Usage:
    python schedule_meeting_recordings.py --dry-run     # show the plan only
    python schedule_meeting_recordings.py               # register/refresh tasks
    python schedule_meeting_recordings.py --daily       # also add the 6 AM refresh task
    python schedule_meeting_recordings.py --list
    python schedule_meeting_recordings.py --clear       # remove every task it owns

Note: the recorder drives a headed browser, so its tasks are created with /IT
("run only when the user is logged on"). A locked or logged-off session cannot
record.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
MEETS_ROOT = PROJECT_ROOT / "Documents Database" / "ERCOT.STKHDR.MEETS"
CALENDAR_LOG = MEETS_ROOT / "_calendar_log"
RECORDER = HERE / "webex_recorder.py"
LOGGER_SCRIPT = HERE / "ercot_calendar_logger.py"

PREFIX = "PowerTalks_Rec_"
DAILY_TASK = "PowerTalks_Rec_DailyRefresh"
DEFAULT_LEAD_MIN = 10
PY = sys.executable

sys.path.insert(0, str(HERE))
import webex_recorder as wr  # noqa: E402  (same folder, used for the shared rules)


# ─── READING THE LOG ─────────────────────────────────────────────────────────
def parse_time(raw: str) -> tuple[int, int] | None:
    """'9:30 AM' -> (9, 30). None when ERCOT has not posted a time."""
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AP])\.?M\.?", raw or "", re.I)
    if not m:
        return None
    hour, minute = int(m.group(1)) % 12, int(m.group(2))
    if m.group(3).upper() == "P":
        hour += 12
    return hour, minute


def upcoming_meetings(days: int) -> list[dict]:
    today = datetime.now().date()
    horizon = today + timedelta(days=days)
    out = []
    for path in sorted(CALENDAR_LOG.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for m in data.get("meetings", []):
            try:
                d = datetime.strptime(m["date"], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue
            if today <= d <= horizon:
                out.append(m)
    out.sort(key=lambda m: (m["date"], parse_time(m.get("time", "")) or (99, 99)))
    return out


def task_name(meeting: dict, committee: str) -> str:
    return f"{PREFIX}{meeting['date']}_{committee}_{wr.slugify(meeting.get('title',''))}"[:200]


# ─── WINDOWS TASK SCHEDULER ──────────────────────────────────────────────────
def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def existing_tasks() -> list[str]:
    code, out = run(["schtasks", "/query", "/fo", "csv", "/nh"])
    if code != 0:
        return []
    names = []
    for line in out.splitlines():
        if PREFIX.lower() in line.lower():
            first = line.split('","')[0].strip('" ').lstrip("\\")
            if first.startswith(PREFIX):
                names.append(first)
    return sorted(set(names))


def create_once_task(name: str, when: datetime, command: str) -> tuple[bool, str]:
    """schtasks takes /sd in the system's short-date order, so try the US
    order this machine wants first and fall back rather than guessing."""
    last = ""
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y"):
        ok, out = _mk(["schtasks", "/create", "/tn", name, "/tr", command,
                       "/sc", "ONCE", "/sd", when.strftime(fmt),
                       "/st", when.strftime("%H:%M"), "/it", "/f"])
        if ok:
            return True, out
        last = out
        if "start date" not in out.lower():
            break
    return False, last


def create_daily_task(name: str, at: str, command: str) -> tuple[bool, str]:
    return _mk(["schtasks", "/create", "/tn", name, "/tr", command,
                "/sc", "DAILY", "/st", at, "/it", "/f"])


def _mk(cmd: list[str]) -> tuple[bool, str]:
    code, out = run(cmd)
    return code == 0, out


def delete_task(name: str) -> bool:
    code, _ = run(["schtasks", "/delete", "/tn", name, "/f"])
    return code == 0


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=35, help="horizon to schedule (default 35)")
    ap.add_argument("--lead-minutes", type=int, default=DEFAULT_LEAD_MIN)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true", help="list the tasks this script owns")
    ap.add_argument("--clear", action="store_true", help="delete every task this script owns")
    ap.add_argument("--daily", action="store_true",
                    help="also register the 6 AM logger+reschedule task")
    ap.add_argument("--daily-at", default="06:00")
    ap.add_argument("--with-logger", action="store_true",
                    help="re-run ercot_calendar_logger.py first, then schedule "
                         "(this is what the daily task invokes)")
    ap.add_argument("--quiet", action="store_true",
                    help="print only the counts (used by the daily task)")
    # PUCT open meetings are already captured by the separate
    # PUCT_OpenMeeting_Daily_Download task, which pulls the official
    # AdminMonitor VOD -- a better source than a Webex guest join.
    ap.add_argument("--exclude", action="append", default=None,
                    metavar="COMMITTEE",
                    help="committee to leave alone (default: PUCT); repeatable")
    ap.add_argument("--no-exclude", action="store_true",
                    help="schedule every committee, PUCT included")
    args = ap.parse_args()
    excluded = set() if args.no_exclude else set(args.exclude or ["PUCT"])

    if args.list:
        names = existing_tasks()
        print(f"{len(names)} task(s) owned by this script:")
        for n in names:
            print("   ", n)
        return 0

    if args.clear:
        names = existing_tasks()
        if args.dry_run:
            print(f"would delete {len(names)} task(s)")
            for n in names:
                print("    -", n)
            return 0
        gone = sum(delete_task(n) for n in names)
        print(f"deleted {gone} of {len(names)} task(s)")
        return 0

    if args.with_logger:
        code, out = run([PY, str(LOGGER_SCRIPT), "--quiet"])
        print(f"calendar logger: {'ok' if code == 0 else 'FAILED'} {out.splitlines()[-1] if out else ''}")

    if not CALENDAR_LOG.is_dir():
        print(f"No calendar log at {CALENDAR_LOG} -- run ercot_calendar_logger.py first.")
        return 1

    known = wr.known_committees()
    now = datetime.now()
    planned: dict[str, str] = {}
    skipped: list[tuple[str, str]] = []
    created = failed = 0

    for m in upcoming_meetings(args.days):
        title = m.get("title", "")
        committee = wr.committee_for(title, known)
        name = task_name(m, committee)

        reason = None
        hhmm = parse_time(m.get("time", ""))
        if committee in excluded:
            reason = f"{committee} excluded (recorded by its own task)"
        elif str(m.get("status", "")).lower().startswith("cancel"):
            reason = "cancelled"
        elif m.get("webcast_url"):
            reason = "webcast by ERCOT"
        elif hhmm is None:
            reason = "no start time posted"
        else:
            start = datetime.strptime(m["date"], "%Y-%m-%d").replace(
                hour=hhmm[0], minute=hhmm[1])
            when = start - timedelta(minutes=args.lead_minutes)
            if when <= now:
                reason = ("already started" if start > now
                          else "start time has passed")
        if reason:
            skipped.append((f"{m['date']} {title[:42]}", reason))
            continue

        cmd = (f'"{PY}" "{RECORDER}" --from-log --date {m["date"]} '
               f'--title "{title}" --quiet')
        planned[name] = f'{when:%Y-%m-%d %H:%M}  {committee:<8} {title[:44]}'
        if args.dry_run:
            continue
        ok, out = create_once_task(name, when, cmd)
        if ok:
            created += 1
        else:
            failed += 1
            print(f"  !! could not create {name}: {out[:160]}")

    # Tasks whose meeting is gone from the plan (cancelled, webcast, or past).
    stale = [n for n in existing_tasks()
             if n != DAILY_TASK and n not in planned]
    removed = 0
    if stale and not args.dry_run:
        removed = sum(delete_task(n) for n in stale)

    verb = "would schedule" if args.dry_run else "scheduled"
    print(f"\n{verb} {len(planned)} recording job(s) "
          f"(lead {args.lead_minutes} min, horizon {args.days} days):")
    if not args.quiet:
        for name in sorted(planned, key=lambda n: planned[n]):
            print("   ", planned[name])
    if skipped and not args.quiet:
        print(f"\nnot scheduled ({len(skipped)}):")
        for what, why in skipped:
            print(f"    {what:<50} {why}")
    if stale:
        print(f"\nstale task(s) {'to remove' if args.dry_run else 'removed'}: "
              f"{len(stale) if args.dry_run else removed}")
        for n in stale:
            print("    -", n)
    if not args.dry_run:
        print(f"\ncreated/refreshed {created}, failed {failed}")

    if args.daily:
        # One command, so /tr stays well inside its 261-character limit.
        daily_cmd = f'"{PY}" "{Path(__file__).resolve()}" --with-logger --quiet'
        if args.dry_run:
            print(f"\nwould register {DAILY_TASK} daily at {args.daily_at}")
        else:
            ok, out = create_daily_task(DAILY_TASK, args.daily_at, daily_cmd)
            print(f"\n{DAILY_TASK} at {args.daily_at}: "
                  f"{'registered' if ok else 'FAILED ' + out[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
