#!/usr/bin/env python3
"""run_routine.py — One-shot driver for the Power.Talks refresh routine.

Runs the full pipeline end-to-end for both tracks and rebuilds the web page:

  MARKET RULES  (Paper Trails)
    1. download   — scrape ercot.com for new revision-request documents
    2. profile    — (re)build each issue's Profile.json from its documents
    3. summarize  — rebuild stale issue summaries (AI executive summary via
                    the Anthropic key in Windows Credential Manager)
    4. web data   — Documents-Submitted list + Paper Trails status arrays

  STAKEHOLDER MEETINGS  (Meeting Tracks)
    5. download   — scrape ercot.com for new committee-meeting documents
    6. profiles   — per-meeting Profile.json (group + meeting summaries)
    7. manifest   — per-committee _manifest.json for the group homepages

  HOT TOPICS  (daily brief)
    8. scaffold   — create HOT.TOPICS/<date>/ (_prep.json + report skeleton)
                    from the week's meetings + source registry, and refresh
                    index.json (the website's date dropdown). Deterministic /
                    headless — the AI summaries + topic ranking are filled in
                    afterward by the Hot Topics Generator skill.

  BUILD
    9. rebuild    — patch the standalone Power.Talks home page bundle

Each step runs as its own subprocess with the correct working directory so the
scripts' relative imports and paths resolve. A failing step is logged and the
routine continues; the final summary lists each step's exit status. Full output
is streamed to the console and appended to a timestamped file under
`Database Codes/logs/`.

Usage:
    py -3 "Database Codes/run_routine.py"                # everything
    py -3 "Database Codes/run_routine.py" --only market  # market rules only
    py -3 "Database Codes/run_routine.py" --only stkhdr  # stakeholder only
    py -3 "Database Codes/run_routine.py" --skip-download # reprocess/rebuild only

Scope is incremental by default (the downloaders only crawl the current year and
skip files already on disk; profiles/summaries only rebuild what changed). For a
full backfill, adjust SINCE_YEAR / ONLY_STALE in the individual scripts.
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB           = os.path.join(PROJECT_ROOT, "Database Codes")
HTML         = os.path.join(PROJECT_ROOT, "html")
LOG_DIR      = os.path.join(DB, "logs")

MKT_CATS = ["nprr", "nogrr", "pgrr", "rmgrr", "scr", "copmgrr"]

PY = sys.executable  # the interpreter running this driver


def _mkt(sub, script):
    return os.path.join(DB, sub, script)


# ─── Pipeline definition ─────────────────────────────────────────────────────
# Each step: (label, [python-args], cwd). cwd matters because some scripts use
# relative paths (gen_mkt_doc_summaries reads "Documents Database/…") or import
# a sibling module (summarize_* imports anthropic_key; gen_stkhdr_manifest
# imports gen_stkhdr_profiles).
def build_steps(args):
    steps = []

    if args.only in (None, "market"):
        # 1. Download
        if not args.skip_download:
            for c in MKT_CATS:
                steps.append((f"MKT download {c.upper()}",
                              [_mkt("download_MKT_Rules", f"download_ercot_{c}.py")],
                              PROJECT_ROOT))
        # 2. Profile
        for c in MKT_CATS:
            steps.append((f"MKT profile {c.upper()}",
                          [_mkt("profile_MKT_Rules", f"profile_ercot_{c}.py")],
                          os.path.join(DB, "profile_MKT_Rules")))
        # 3. Summarize (AI; ONLY_STALE=True inside each script)
        for c in MKT_CATS:
            steps.append((f"MKT summarize {c.upper()}",
                          [_mkt("summarize_MKT_Rules", f"summarize_ercot_{c}.py")],
                          os.path.join(DB, "summarize_MKT_Rules")))
        # 3b. Comment-derived sections: ERCOT/IMM Opinions (report-table
        #     extraction) + Stakeholder Key Debates (AI). Runs after summarize;
        #     summarize preserves existing values, so this only fills issues that
        #     are new or still missing them (resume-skip inside the script).
        for c in MKT_CATS:
            steps.append((f"MKT stakeholder sections {c.upper()}",
                          [_mkt("summarize_MKT_Rules", "gen_stakeholder_sections.py"),
                           c.upper(), "--all"],
                          os.path.join(DB, "summarize_MKT_Rules")))
        # 4. Web data for Paper Trails
        steps.append(("MKT web: documents-submitted",
                      [os.path.join(DB, "gen_mkt_doc_summaries.py")],
                      PROJECT_ROOT))
        steps.append(("MKT web: paper-trails status arrays",
                      [os.path.join(HTML, "regen_paper_trails_data.py")],
                      HTML))

    if args.only in (None, "stkhdr"):
        stk = os.path.join(DB, "download_STKHDR_Meets")
        # 5. Download
        if not args.skip_download:
            steps.append(("STKHDR download (all committees)",
                          [os.path.join(stk, "download_ercot_stkhdr.py")],
                          stk))
        # 6. Per-meeting profiles (script uses a project-root-relative ROOT, so
        #    it must run from PROJECT_ROOT, not its own folder)
        steps.append(("STKHDR meeting profiles",
                      [os.path.join(stk, "gen_stkhdr_profiles.py")],
                      PROJECT_ROOT))
        # 7. Group manifests
        steps.append(("STKHDR group manifests",
                      [os.path.join(stk, "gen_stkhdr_manifest.py")],
                      stk))

        # 8. Hot Topics scaffold — reads the stakeholder meetings just
        #    downloaded above to find "within the week" meetings, writes
        #    HOT.TOPICS/<date>/{_prep.json, skeleton}, and refreshes index.json
        #    (the website's date dropdown). No web/AI calls; the summaries and
        #    ranking are filled later by the Hot Topics Generator skill.
        steps.append(("HOT TOPICS scaffold + index",
                      [os.path.join(DB, "hot_topics", "gen_hot_topics.py")],
                      PROJECT_ROOT))

    # 9. Rebuild the standalone web bundle (once, at the end)
    if not args.no_rebuild:
        steps.append(("BUILD rebuild standalone page",
                      [os.path.join(HTML, "rebuild_standalone.py")],
                      HTML))

    return steps


def run(logf):
    def emit(line):
        # The log is UTF-8; the console may be cp1252 (Windows) or absent (Task
        # Scheduler). Never let an un-encodable child character abort a step.
        try:
            print(line, flush=True)
        except (UnicodeEncodeError, OSError):
            enc = (getattr(sys.stdout, "encoding", None) or "ascii")
            try:
                sys.stdout.buffer.write((line + "\n").encode(enc, "replace"))
                sys.stdout.flush()
            except Exception:
                pass
        logf.write(line + "\n")
        logf.flush()

    parser = argparse.ArgumentParser(description="Power.Talks refresh routine")
    parser.add_argument("--only", choices=["market", "stkhdr"],
                        help="run only one track (default: both)")
    parser.add_argument("--skip-download", action="store_true",
                        help="reprocess/rebuild from documents already on disk")
    parser.add_argument("--no-rebuild", action="store_true",
                        help="skip the final standalone-page rebuild")
    args = parser.parse_args()

    steps = build_steps(args)
    emit("=" * 72)
    emit(f"Power.Talks routine — {datetime.now():%Y-%m-%d %H:%M:%S}")
    emit(f"Python: {PY}")
    emit(f"Steps:  {len(steps)}"
         + (f"  (only={args.only})" if args.only else "")
         + ("  [skip-download]" if args.skip_download else "")
         + ("  [no-rebuild]" if args.no_rebuild else ""))
    emit("=" * 72)

    results = []
    t0 = time.time()
    for i, (label, cmd, cwd) in enumerate(steps, 1):
        emit("")
        emit(f"[{i}/{len(steps)}] {label}")
        emit(f"    $ {os.path.basename(cmd[0])}   (cwd={os.path.relpath(cwd, PROJECT_ROOT)})")
        start = time.time()
        child_env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        try:
            proc = subprocess.run(
                [PY] + cmd, cwd=cwd, env=child_env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for out_line in (proc.stdout or "").splitlines():
                emit(f"    | {out_line}")
            code = proc.returncode
        except Exception as e:  # script missing, interpreter error, etc.
            emit(f"    ! launch failed: {e}")
            code = -1
        dt = time.time() - start
        status = "OK" if code == 0 else f"FAIL({code})"
        emit(f"    -> {status} in {dt:.1f}s")
        results.append((label, status, dt))

    # ─── Summary ────────────────────────────────────────────────────────────
    total = time.time() - t0
    emit("")
    emit("=" * 72)
    emit(f"SUMMARY  ({total/60:.1f} min total)")
    emit("=" * 72)
    failed = 0
    for label, status, dt in results:
        if status != "OK":
            failed += 1
        emit(f"  {status:<10} {dt:>6.1f}s  {label}")
    emit("-" * 72)
    emit(f"  {len(results) - failed} ok, {failed} failed")
    emit("=" * 72)
    return 1 if failed else 0


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # older/redirected streams without reconfigure
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"routine_{datetime.now():%Y%m%d_%H%M%S}.log")
    with open(log_path, "w", encoding="utf-8") as logf:
        rc = run(logf)
        print(f"\nLog written to: {log_path}", flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
