#!/usr/bin/env python3
"""run_gallery_routine.py - the GALLERY chart routine driver.

A standalone routine, deliberately separate from `Database Codes/run_routine.py`
(the 1 AM Power.Talks daily refresh). It is kept apart for three reasons:

  * it reads thousands of PDFs and workbooks, which takes far longer than any
    step of the daily refresh and would push that run past its window;
  * it opens thousands of documents, which must not race another automation;
  * it spends its own AI budget, so a slow backfill here can never eat the
    quota the nightly summarizers depend on.

Steps
-----
  1. keywords  - refresh `gallery.keyword_id` from the curated market-keyword
                 list, so the chart vocabulary is current before anything is
                 matched against it. (`Database Codes/sync_keyword_ids.py`;
                 skip with --skip-keywords when the daily refresh just ran it.)
  2. extract   - find charts in new/changed PDFs, write
                 the PNGs to Documents Database/GALLERY, and upsert
                 gallery_charts + gallery_keywords.
  3. verify    - re-assert that gallery_charts.keywords only ever contains
                 values backed by gallery_keywords, repairing any drift.

Each step runs as its own subprocess, so one failing step does not take the
rest down; the summary lists every step's exit status. Everything is streamed
to the console and appended to a timestamped log under
`Documents Database/GALLERY/routine_log/`.

Usage
-----
    py -3 "Database Codes/download_GALLERY_charts/run_gallery_routine.py"
    py -3 ... run_gallery_routine.py --ai-budget 150 --max-docs 400
    py -3 ... run_gallery_routine.py --no-ai          # prefilter only, no quota
    py -3 ... run_gallery_routine.py --dry-run        # detect and report only
    py -3 ... run_gallery_routine.py --group BOARD --since 2026-01-01

Exit code 0 when every step succeeded, 1 if any step failed, 2 when the
extractor stopped because the AI subscription window was used up (the
remaining documents are simply picked up by the next run).
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(DB_DIR)
LOG_DIR = os.path.join(PROJECT_ROOT, "Documents Database", "GALLERY", "routine_log")

EXTRACTOR = os.path.join(HERE, "gallery_charts_extractions_generations.py")
SYNC_KEYWORDS = os.path.join(DB_DIR, "sync_keyword_ids.py")

PY = sys.executable

# The extractor signals "AI subscription window used up" with this code; the
# routine passes it through so the scheduler can tell a quota pause apart from
# a real failure.
RC_AI_QUOTA = 2


def build_steps(args):
    steps = []
    if not args.skip_keywords:
        steps.append(("GALLERY sync keyword vocabulary -> gallery.keyword_id",
                      [SYNC_KEYWORDS] + (["--dry-run"] if args.dry_run else ["--quiet"]),
                      DB_DIR))

    extract = [EXTRACTOR, "--quiet"]
    if args.dry_run:
        extract.append("--dry-run")
    if args.no_ai:
        extract.append("--no-ai")
    else:
        extract += ["--ai-budget", str(args.ai_budget)]
    if args.max_docs:
        extract += ["--max-docs", str(args.max_docs)]
    if args.rescan:
        extract.append("--rescan")
    for flag in ("group", "since", "until"):
        val = getattr(args, flag)
        if val:
            extract += [f"--{flag}", val]
    steps.append(("GALLERY extract charts -> PNG + gallery_charts", extract, HERE))

    if not args.dry_run:
        steps.append(("GALLERY verify keyword invariant",
                      [EXTRACTOR, "--verify-only", "--quiet"], HERE))
    return steps


def run(logf, args):
    def emit(line=""):
        try:
            print(line, flush=True)
        except (UnicodeEncodeError, OSError):
            enc = getattr(sys.stdout, "encoding", None) or "ascii"
            try:
                sys.stdout.buffer.write((line + "\n").encode(enc, "replace"))
                sys.stdout.flush()
            except Exception:
                pass
        logf.write(line + "\n")
        logf.flush()

    steps = build_steps(args)
    emit("=" * 72)
    emit(f"Power.Talks GALLERY chart routine - {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    emit(f"Python: {PY}")
    emit(f"Steps:  {len(steps)}"
         + ("  [dry-run]" if args.dry_run else "")
         + ("  [no-ai]" if args.no_ai else f"  [ai-budget={args.ai_budget}]")
         + (f"  [max-docs={args.max_docs}]" if args.max_docs else "")
         + ("  [rescan]" if args.rescan else ""))
    emit("=" * 72)

    results = []
    quota = False
    t0 = time.time()
    for i, (label, cmd, cwd) in enumerate(steps, 1):
        emit("")
        emit(f"[{i}/{len(steps)}] {label}")
        emit(f"    $ {os.path.basename(cmd[0])}   "
             f"(cwd={os.path.relpath(cwd, PROJECT_ROOT)})")
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
        except Exception as e:
            emit(f"    ! launch failed: {e}")
            code = -1
        dt_s = time.time() - start
        if code == RC_AI_QUOTA and "extract" in label:
            status, quota = "AI-QUOTA", True
        else:
            status = "OK" if code == 0 else f"FAIL({code})"
        emit(f"    -> {status} in {dt_s:.1f}s")
        results.append((label, status, dt_s))

    total = time.time() - t0
    emit("")
    emit("=" * 72)
    emit(f"SUMMARY  ({total/60:.1f} min total)")
    emit("=" * 72)
    failed = 0
    for label, status, dt_s in results:
        if status.startswith("FAIL"):
            failed += 1
        emit(f"  {status:<10} {dt_s:>6.1f}s  {label}")
    emit("-" * 72)
    emit(f"  {len(results) - failed} ok, {failed} failed"
         + ("  (stopped early: AI subscription window used up; the remaining "
            "documents are left for the next run)" if quota else ""))
    emit("=" * 72)
    if failed:
        return 1
    return RC_AI_QUOTA if quota else 0


def main():
    p = argparse.ArgumentParser(description="Power.Talks GALLERY chart routine")
    p.add_argument("--skip-keywords", action="store_true",
                   help="do not refresh gallery.keyword_id first")
    p.add_argument("--no-ai", action="store_true",
                   help="prefilter only; spends no AI quota")
    p.add_argument("--ai-budget", type=int, default=30,
                   help="AI calls (one per document) this run may spend "
                        "(default 30, sized for Opus in lean mode; on "
                        "Haiku this was 400)")
    p.add_argument("--max-docs", type=int, default=0,
                   help="stop after this many documents (0 = no cap)")
    p.add_argument("--dry-run", action="store_true",
                   help="detect and report only: no PNG, no DB write")
    p.add_argument("--rescan", action="store_true",
                   help="re-read every document, ignoring the unchanged check")
    p.add_argument("--group", help="limit to one committee folder, e.g. BOARD")
    p.add_argument("--since", help="only meetings on/after this date (YYYY-MM-DD)")
    p.add_argument("--until", help="only meetings on/before this date (YYYY-MM-DD)")
    args = p.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(
        LOG_DIR, f"gallery_routine_{dt.datetime.now():%Y%m%d_%H%M%S}.log")
    with open(log_path, "w", encoding="utf-8") as logf:
        rc = run(logf, args)
        print(f"\nLog written to: {log_path}", flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
