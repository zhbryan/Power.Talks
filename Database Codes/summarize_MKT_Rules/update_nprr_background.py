#!/usr/bin/env python3
"""
Refresh only the `background` field of each NPRR Summary.json from the checked
Reason-for-Revision option(s) now stored in the sibling Profile.json.

Background used to copy *every* reason option; profile_ercot_nprr.py now keeps
only the box(es) the sponsor actually checked (reason_for_revision). This
propagates that to the homepage "Background" section without re-running the
(AI) summarizer. When no box is checked, background becomes "" and the homepage
hides the section. Nothing else in Summary.json is touched.

The daily routine's full summarize run does the same join, so this is only for
a one-time in-place refresh of existing summaries.
"""

import os
import re
import json

BASE_DIR = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES\NPRR"


def reason_to_background(reason):
    if isinstance(reason, list):
        return '; '.join(reason)
    return reason or ''


def main():
    folders = sorted(
        [d for d in os.listdir(BASE_DIR)
         if os.path.isdir(os.path.join(BASE_DIR, d)) and re.match(r'NPRR\d+', d)],
        key=lambda x: int(re.search(r'\d+', x).group()))

    changed = missing = 0
    for folder_name in folders:
        n = int(re.search(r'\d+', folder_name).group())
        quick = os.path.join(BASE_DIR, folder_name, "Quick runs")
        prof_path = os.path.join(quick, f"NPRR{n} Profile.json")
        summ_path = os.path.join(quick, f"NPRR{n} Summary.json")
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
        print(f"[BG] NPRR{n:>4}  {new_bg[:70] or '(empty)'}")

    print(f"\nDone: {changed} summaries updated, {missing} without profile/summary.")


if __name__ == "__main__":
    main()
