#!/usr/bin/env python3
"""
Backfill the `impacts_summary` field into each NPRR Summary.json.

"Potential Impacts" used to show the raw Justification text truncated to 500
chars under a "Business Case / Justification" label. It now shows an AI summary
of the "Justification of Reason for Revision and Market Impacts" section
(profile `business_case`). This script fills that field into existing summaries
without re-running the (separate) executive-summary generation, and drops the
old `impacts` array. The daily routine's full summarize run produces the same
field going forward.

One Haiku call per issue that has a business_case; issues already carrying a
non-empty impacts_summary (and no stale `impacts` key) are skipped, so the run
is resumable. Idempotent.
"""

import os
import re
import sys
import json

# The Windows console pipe defaults to cp1252; AI summaries can contain
# characters it cannot encode. Never let a log line crash the run mid-write.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Reuse the summarizer's AI client, model settings, and prompt.
from summarize_ercot_nprr import ai_impacts_summary, get_ai, _ai_usage, AI_MODEL

BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES\NPRR"


def preflight():
    """Confirm the API actually works before touching any files. ai_impacts_summary
    swallows failures and returns a raw excerpt, which would silently poison every
    summary and mark it 'done'. Abort loudly instead if the API is unavailable."""
    get_ai().messages.create(
        model=AI_MODEL, max_tokens=8,
        messages=[{"role": "user", "content": "Reply with the word OK."}])


def main():
    try:
        preflight()
    except Exception as e:
        print(f"ABORT — API preflight failed, no files touched: {e}")
        raise SystemExit(1)

    folders = sorted(
        [d for d in os.listdir(BASE_DIR)
         if os.path.isdir(os.path.join(BASE_DIR, d)) and re.match(r'NPRR\d+', d)],
        key=lambda x: int(re.search(r'\d+', x).group()))

    changed = skipped = missing = 0
    for folder_name in folders:
        n = int(re.search(r'\d+', folder_name).group())
        quick = os.path.join(BASE_DIR, folder_name, "Quick runs")
        prof_path = os.path.join(quick, f"NPRR{n} Profile.json")
        summ_path = os.path.join(quick, f"NPRR{n} Summary.json")
        if not (os.path.exists(prof_path) and os.path.exists(summ_path)):
            missing += 1
            continue

        with open(summ_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)

        # Already backfilled (has impacts_summary, old key removed) -> skip.
        if summary.get('impacts_summary') and 'impacts' not in summary:
            skipped += 1
            continue

        with open(prof_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        biz_case = profile.get('business_case')
        title = profile.get('title') or f"NPRR{n}"
        sections = profile.get('governing_document_sections', [])

        summary['impacts_summary'] = ai_impacts_summary(f"NPRR{n}", title, biz_case, sections)
        summary.pop('impacts', None)  # drop the old labeled array

        with open(summ_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        changed += 1
        tag = (summary['impacts_summary'][:70] or '(no business case)')
        print(f"[IMP] NPRR{n:>4}  {tag}")

    print(f"\nDone: {changed} updated, {skipped} already done, {missing} without profile/summary.")
    print(f"AI: {_ai_usage['calls']} calls ({AI_MODEL}), "
          f"{_ai_usage['input_tokens']:,} in / {_ai_usage['output_tokens']:,} out tokens.")


if __name__ == "__main__":
    main()
