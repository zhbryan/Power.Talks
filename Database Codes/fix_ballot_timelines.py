#!/usr/bin/env python3
"""
Rewrite the `timeline` array of every existing market-rule Summary.json using
the corrected ballot parser in summarize_MKT_Rules/ballot_votes.py.

Why this exists: the old extract_votes() never opened the ballot workbook. It
scraped printable byte runs out of the raw .xls and regex'd for "<n> For", so
the first number anywhere upstream of the word "for" became the vote count --
"table NPRR1343 for further review by CMWG" was published as "1343 For".
Every ballot row in every Stakeholder Discussion Timeline was affected.

This is a data-only retrofit: build_timeline() reads filenames and ballot
workbooks, so it needs no AI calls and no Word automation. Everything else in
each Summary.json (executive summary, impacts, ERCOT/IMM opinions, key
debates) is left byte-for-byte alone.

Usage:
    python fix_ballot_timelines.py --dry-run         # report, change nothing
    python fix_ballot_timelines.py                   # apply
    python fix_ballot_timelines.py --only NPRR1343   # one issue
"""

import argparse
import importlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "summarize_MKT_Rules"))

CATEGORIES = [
    ("NPRR",    "summarize_ercot_nprr"),
    ("NOGRR",   "summarize_ercot_nogrr"),
    ("PGRR",    "summarize_ercot_pgrr"),
    ("RMGRR",   "summarize_ercot_rmgrr"),
    ("SCR",     "summarize_ercot_scr"),
    ("COPMGRR", "summarize_ercot_copmgrr"),
]


def patch_docx(path, timeline):
    """Rewrite the Outcome column of the Stakeholder Discussion Timeline table
    in an already-written Summary.docx. Only the outcome cells are touched, so
    the rest of the report is left exactly as the summarizer wrote it. Returns
    the number of cells changed, or -1 if the table did not line up."""
    from docx import Document

    doc = Document(path)
    by_key = {(ev["date"], ev["body"], ev["action"]): ev["notes"] for ev in timeline}
    fixed = 0
    for table in doc.tables:
        head = [c.text.strip() for c in table.rows[0].cells]
        if head[:4] != ["Date", "Body", "Action", "Outcome"]:
            continue
        if len(table.rows) - 1 != len(timeline):
            return -1
        for row in table.rows[1:]:
            cells = row.cells
            key = (cells[0].text.strip(), cells[1].text.strip(), cells[2].text.strip())
            want = by_key.get(key)
            if want is None:
                return -1
            cell = cells[3]
            if cell.text.strip() == want:
                continue
            para = cell.paragraphs[0]
            if para.runs:
                para.runs[0].text = want
                for extra in para.runs[1:]:
                    extra.text = ""
            else:
                cell.text = want
            fixed += 1
        if fixed:
            doc.save(path)
        return fixed
    return 0


def issue_folders(base_dir, cat):
    pat = re.compile(re.escape(cat) + r"\d+$")
    if not os.path.isdir(base_dir):
        return []
    names = [d for d in os.listdir(base_dir)
             if pat.match(d) and os.path.isdir(os.path.join(base_dir, d))]
    return sorted(names, key=lambda x: int(re.search(r"\d+", x).group()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", action="append", default=None,
                    help="issue id such as NPRR1343; repeatable")
    args = ap.parse_args()

    only = set(x.upper() for x in (args.only or []))
    scanned = changed = rows_fixed = missing = 0
    docx_fixed = docx_skipped = 0

    for cat, modname in CATEGORIES:
        mod = importlib.import_module(modname)
        base_dir = mod.BASE_DIR
        for issue_id in issue_folders(base_dir, cat):
            if only and issue_id.upper() not in only:
                continue
            folder = os.path.join(base_dir, issue_id)
            jpath = os.path.join(folder, "Quick runs", f"{issue_id} Summary.json")
            if not os.path.exists(jpath):
                missing += 1
                continue
            scanned += 1
            try:
                with io.open(jpath, encoding="utf-8") as f:
                    data = json.load(f)
            except (ValueError, OSError) as e:
                print(f"  !! {issue_id}: cannot read Summary.json ({e})")
                continue

            events = mod.build_timeline(folder)
            new_tl = [{"date": ev["date"], "body": ev["body"],
                       "action": ev["action"], "notes": ev["outcome"]}
                      for ev in events]
            # The .docx carries the same table and is patched whether or not
            # the JSON still needs it, so a rerun repairs reports written
            # before this fix landed.
            dpath = os.path.join(folder, "Quick runs", f"{issue_id} Summary.docx")
            if os.path.exists(dpath) and not args.dry_run:
                try:
                    n = patch_docx(dpath, new_tl)
                except Exception as e:
                    n = -1
                    print(f"  !! {issue_id}: docx patch failed ({e})")
                if n > 0:
                    docx_fixed += 1
                elif n < 0:
                    docx_skipped += 1
                    print(f"  -- {issue_id}: docx timeline table does not line up, left alone")

            old_tl = data.get("timeline", [])
            if new_tl == old_tl:
                continue

            changed += 1
            old_by_key = {(e.get("date"), e.get("body"), e.get("action")): e.get("notes")
                          for e in old_tl}
            for ev in new_tl:
                key = (ev["date"], ev["body"], ev["action"])
                was = old_by_key.get(key)
                if was != ev["notes"]:
                    rows_fixed += 1
                    print(f"  {issue_id} {ev['date']} {ev['body']:<5} "
                          f"{was!r} -> {ev['notes']!r}")

            if not args.dry_run:
                data["timeline"] = new_tl
                tmp = jpath + ".tmp"
                with io.open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                os.replace(tmp, jpath)

    verb = "would change" if args.dry_run else "changed"
    print(f"\n{scanned} Summary.json scanned, {verb} {changed} "
          f"({rows_fixed} timeline row(s)); {missing} issue(s) have no summary yet.")
    if not args.dry_run:
        print(f"{docx_fixed} Summary.docx timeline table(s) repaired"
              + (f", {docx_skipped} left alone" if docx_skipped else ""))


if __name__ == "__main__":
    main()
