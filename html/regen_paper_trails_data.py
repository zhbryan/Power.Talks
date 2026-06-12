"""
regen_paper_trails_data.py — Regenerate the Paper Trails list arrays in
html/src/data.jsx from the Documents Database.

For every category, walks Documents Database/ERCOT.MKT.RULES/<CAT>/,
reads each issue's Quick runs Profile.json (status, title; title falls back
to Summary.json), buckets issues by status, and rewrites the matching
`const <CAT>_<STATUS> = [...]` blocks in data.jsx in place. Arrays that do
not already exist in data.jsx are left out (a warning is printed instead).

After running this, run rebuild_standalone.py to update the bundled page.

Usage:  py -3 regen_paper_trails_data.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

DB = Path(r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES")
DATA_JSX = Path(__file__).parent / "src" / "data.jsx"
RUN_LOG = Path(__file__).parent / "paper_trails_run_log.txt"
CATEGORIES = ["NPRR", "COPMGRR", "PGRR", "SCR", "NOGRR", "RMGRR"]
STATUSES = ["PENDING", "APPROVED", "WITHDRAWN", "REJECTED"]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def collect(cat):
    buckets = {}
    cat_dir = DB / cat
    folders = sorted(
        (d for d in cat_dir.iterdir() if d.is_dir() and re.fullmatch(rf"{cat}\d+", d.name)),
        key=lambda d: int(re.search(r"\d+", d.name).group()),
    )
    for folder in folders:
        issue_id = folder.name
        n = int(re.search(r"\d+", issue_id).group())
        quick = folder / "Quick runs"
        profile = load_json(quick / f"{issue_id} Profile.json")
        summary = load_json(quick / f"{issue_id} Summary.json")
        title = profile.get("title") or summary.get("title") or ""
        if title in (issue_id, str(n)):
            title = ""
        status = (profile.get("status") or "Approved").upper()
        title = title.replace('"', "'").strip()
        buckets.setdefault(status, []).append(f'  {{ n: {n}, title: "{title}" }},')
    return buckets


def main():
    text = DATA_JSX.read_text(encoding="utf-8")
    replaced, skipped = [], []

    for cat in CATEGORIES:
        buckets = collect(cat)
        for status in STATUSES:
            items = buckets.get(status, [])
            name = f"{cat}_{status}"
            pattern = re.compile(rf"(const {name} = \[\n)(.*?)(\n\];)", re.DOTALL)
            m = pattern.search(text)
            if not m:
                if items:
                    skipped.append(f"{name} ({len(items)} issues, no array in data.jsx)")
                continue
            old_count = m.group(2).count("{ n:")
            text = text[: m.start(2)] + "\n".join(items) + text[m.end(2):]
            replaced.append(f"{name}: {old_count} -> {len(items)}")

    DATA_JSX.write_text(text, encoding="utf-8")
    print("Replaced arrays:")
    for r in replaced:
        print(f"  {r}")
    if skipped:
        print("Skipped (no existing array):")
        for s in skipped:
            print(f"  {s}")
    print(f"\nWrote {DATA_JSX}")
    print("Now run:  py -3 rebuild_standalone.py")

    # Run log — main changes only (arrays whose counts moved), appended per run.
    changed = [r for r in replaced if r.split(": ")[1].split(" -> ")[0] != r.split(" -> ")[1]]
    with open(RUN_LOG, "a", encoding="utf-8") as log:
        log.write(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} regen_paper_trails_data ===\n")
        if changed:
            for c in changed:
                log.write(f"  {c}\n")
        else:
            log.write("  no list changes\n")
        for s in skipped:
            log.write(f"  SKIPPED {s}\n")
    print(f"Run log appended: {RUN_LOG}")


if __name__ == "__main__":
    main()
