#!/usr/bin/env python3
"""
Refresh the `background` field of every market-rule Summary.json from the
checked Reason-for-Revision option(s) now stored in the sibling Profile.json,
for all six categories (NPRR/COPMGRR/PGRR/SCR/NOGRR/RMGRR).

Background used to copy *every* reason option; profile_ercot_<cat>.py now keeps
only the box(es) the sponsor actually checked (reason_for_revision). This
propagates that to each homepage's "Background" / "Reason for Revision" section
without re-running the (AI) summarizers. When no box is checked, background
becomes "" and the homepage hides the section. Nothing else is touched.

The daily routine's full summarize run does the same join, so this is only a
one-time in-place refresh of existing summaries. Idempotent. Optional args
limit the run to specific categories, e.g.  python update_reason_background.py SCR NOGRR
"""

import os
import re
import sys
import json

ROOT = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES"
CATEGORIES = ["NPRR", "COPMGRR", "PGRR", "SCR", "NOGRR", "RMGRR"]


def reason_to_background(reason):
    if isinstance(reason, list):
        return '; '.join(reason)
    return reason or ''


def process_category(cat):
    base = os.path.join(ROOT, cat)
    if not os.path.isdir(base):
        print(f"{cat}: no directory, skipped.")
        return
    folders = sorted(
        [d for d in os.listdir(base)
         if os.path.isdir(os.path.join(base, d)) and re.match(rf'{cat}\d+$', d)],
        key=lambda x: int(re.search(r'\d+', x).group()))

    changed = missing = 0
    for folder in folders:
        quick = os.path.join(base, folder, "Quick runs")
        # Folder name is the issue id, which is also the file prefix.
        prof_path = os.path.join(quick, f"{folder} Profile.json")
        summ_path = os.path.join(quick, f"{folder} Summary.json")
        if not (os.path.exists(prof_path) and os.path.exists(summ_path)):
            missing += 1
            continue

        with open(prof_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        with open(summ_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)

        new_bg = reason_to_background(profile.get('reason_for_revision'))
        if summary.get('background', '') == new_bg:
            continue

        summary['background'] = new_bg
        with open(summ_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        changed += 1

    print(f"{cat:8} {changed} summaries updated, {missing} without profile/summary.")


def main():
    cats = [c.upper() for c in sys.argv[1:]] or CATEGORIES
    for cat in cats:
        process_category(cat)


if __name__ == "__main__":
    main()
