#!/usr/bin/env python3
"""gen_hot_topics.py — deterministic prep for the daily ERCOT Hot Topics report.

This does the mechanical parts of the Hot Topics workflow so the AI step (news
gathering, summarization, topic ranking — done by Claude via the "Hot Topics
Generator" skill) only has to fill in content:

  1. Loads the maintained source registry (hot_topics/sources.json).
  2. Auto-discovers ERCOT stakeholder committee meetings whose dated folder on
     disk falls within `within_days` of the report date (the "within the week"
     meetings), with their document lists.
  3. Creates the dated output folder  HOT.TOPICS/<YYYY-MM-DD>/  and writes:
       - _prep.json          : sources + recent meetings + target paths (input
                               for the AI step)
       - hot_topics_<date>.md: a report skeleton the AI step fills in.

It never calls any web/LLM API — it's safe to run headless in the daily routine.
The AI content is added afterwards by running the skill against _prep.json.

Usage:
    py -3 "Database Codes/hot_topics/gen_hot_topics.py"                # today
    py -3 "Database Codes/hot_topics/gen_hot_topics.py" --date 2026-07-30
    py -3 "Database Codes/hot_topics/gen_hot_topics.py" --days 7       # override window
"""

import argparse
import json
import os
from datetime import date, datetime, timedelta

# ─── Paths ───────────────────────────────────────────────────────────────────
HERE         = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))            # …/Power.Talks
SOURCES_JSON = os.path.join(HERE, "sources.json")
STKHDR_ROOT  = os.path.join(PROJECT_ROOT, "Documents Database", "ERCOT.STKHDR.MEETS")
OUT_ROOT     = os.path.join(PROJECT_ROOT, "Documents Database", "HOT.TOPICS")

DATE_FMT = "%Y-%m-%d"


def load_sources():
    with open(SOURCES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def write_index():
    """Scan HOT.TOPICS/<date>/hot_topics_<date>.md and write index.json — the
    newest-first list of available report dates the website's Hot Topics page
    reads to populate its date dropdown. Returns the list of dates written."""
    entries = []
    if os.path.isdir(OUT_ROOT):
        for name in os.listdir(OUT_ROOT):
            d = _iso_or_none(name)
            if d is None:
                continue
            fname = f"hot_topics_{name}.md"
            fpath = os.path.join(OUT_ROOT, name, fname)
            if not os.path.isfile(fpath):
                continue
            title = f"ERCOT Hot Topics — {name}"
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
            except OSError:
                pass
            entries.append({"date": name, "file": fname, "title": title})
    entries.sort(key=lambda e: e["date"], reverse=True)   # newest first
    index = {"generated_at": datetime.now().isoformat(timespec="seconds"),
             "dates": entries}
    os.makedirs(OUT_ROOT, exist_ok=True)
    with open(os.path.join(OUT_ROOT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    return entries


def _iso_or_none(name):
    """Parse a 'YYYY-MM-DD' folder name into a date, else None."""
    try:
        return datetime.strptime(name, DATE_FMT).date()
    except ValueError:
        return None


def discover_recent_meetings(report_date, within_days):
    """Scan ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD> for meetings whose date
    is within `within_days` before (or on) the report date. Returns a list of
    dicts sorted newest-first."""
    cutoff = report_date - timedelta(days=within_days)
    found = []
    if not os.path.isdir(STKHDR_ROOT):
        return found
    for committee in sorted(os.listdir(STKHDR_ROOT)):
        cdir = os.path.join(STKHDR_ROOT, committee)
        if not os.path.isdir(cdir):
            continue
        for entry in os.listdir(cdir):
            mdate = _iso_or_none(entry)
            if mdate is None or not (cutoff <= mdate <= report_date):
                continue
            mdir = os.path.join(cdir, entry)
            docs = sorted(
                f for f in os.listdir(mdir)
                if os.path.isfile(os.path.join(mdir, f))
                and not f.endswith(".extracted")
            )
            found.append({
                "committee": committee,
                "date": entry,
                "path": os.path.relpath(mdir, PROJECT_ROOT).replace("\\", "/"),
                "doc_count": len(docs),
                "docs": docs,
            })
    found.sort(key=lambda m: (m["date"], m["committee"]), reverse=True)
    return found


def enabled_sources(reg):
    """Flatten the registry into the list of enabled web/primary sources."""
    out = []
    for group, items in reg["sources"].items():
        if group == "stakeholder_meetings":
            continue  # handled by disk discovery
        for s in items:
            if s.get("enabled") and s.get("url"):
                out.append({
                    "id": s["id"], "name": s["name"], "url": s["url"],
                    "group": group, "rank": s.get("rank"), "notes": s.get("notes", ""),
                })
    return out


def build_skeleton(report_date, reg, sources, meetings):
    d = report_date.strftime(DATE_FMT)
    lines = [
        f"# ERCOT Hot Topics — {d}",
        "",
        f"*Generated {datetime.now():%Y-%m-%d %H:%M}. Scope: topics relevant to the "
        f"ERCOT power market only, within the last {reg['within_days']} days.*",
        "",
        "> **AI step not yet run.** This is a scaffold produced by "
        "`gen_hot_topics.py`. Run the **Hot Topics Generator** skill to fill the "
        "summaries and topic ranking below from `_prep.json`.",
        "",
        "## 🔥 Top Hot Topics (ranked by frequency across sources)",
        "",
        "| # | Topic | Mentions | Sources | Why it matters |",
        "|---|-------|:--------:|---------|----------------|",
        "| 1 | _TBD_ | _n_ | _…_ | _…_ |",
        "",
        "## 📋 Source Summaries",
        "",
    ]

    lines.append("### ERCOT.com (official)")
    for s in sources:
        if s["group"] == "ercot_official":
            lines.append(f"- **{s['name']}** — {s['url']}")
            lines.append("  - _summary TBD_")
    lines.append("")

    lines.append(f"### Recent stakeholder meetings (within {reg['within_days']} days)")
    if meetings:
        for m in meetings:
            lines.append(f"- **{m['committee']} — {m['date']}** "
                         f"({m['doc_count']} docs) · `{m['path']}`")
            lines.append("  - _summary TBD_")
    else:
        lines.append("- _No committee meetings on disk in the window. "
                     "Check https://www.ercot.com/committees for newly posted meetings._")
    lines.append("")

    lines.append("### PUCT")
    for s in sources:
        if s["group"] == "puct":
            lines.append(f"- **{s['name']}** — {s['url']}")
            lines.append("  - _summary TBD_")
    lines.append("")

    lines.append("### Electricity-market news sites")
    for s in sorted((x for x in sources if x["group"] == "news_sites"),
                    key=lambda x: x.get("rank") or 99):
        lines.append(f"- **{s['name']}** — {s['url']}")
        lines.append("  - _summary TBD_")
    lines.append("")

    lines.append("## 🗂️ Sources checked")
    lines.append("")
    for s in sources:
        lines.append(f"- [{s['group']}] {s['name']} — {s['url']}")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Prep the daily ERCOT Hot Topics report")
    ap.add_argument("--date", help="report date YYYY-MM-DD (default: today)")
    ap.add_argument("--days", type=int, help="override the within-days window")
    ap.add_argument("--index-only", action="store_true",
                    help="only refresh HOT.TOPICS/index.json for the website (no scaffolding)")
    args = ap.parse_args()

    if args.index_only:
        dates = write_index()
        print(f"Wrote HOT.TOPICS/index.json  ({len(dates)} report date(s))")
        for e in dates:
            print(f"  - {e['date']}  {e['file']}")
        return

    report_date = (datetime.strptime(args.date, DATE_FMT).date()
                   if args.date else date.today())

    reg = load_sources()
    if args.days:
        reg["within_days"] = args.days
    within = reg["within_days"]

    sources  = enabled_sources(reg)
    meetings = discover_recent_meetings(report_date, within)

    out_dir = os.path.join(OUT_ROOT, report_date.strftime(DATE_FMT))
    os.makedirs(out_dir, exist_ok=True)

    prep = {
        "report_date": report_date.strftime(DATE_FMT),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "within_days": within,
        "ercot_market_focus": reg["ercot_market_focus"],
        "web_sources": sources,
        "recent_meetings": meetings,
        "output_dir": os.path.relpath(out_dir, PROJECT_ROOT).replace("\\", "/"),
        "report_file": f"hot_topics_{report_date.strftime(DATE_FMT)}.md",
    }
    prep_path = os.path.join(out_dir, "_prep.json")
    with open(prep_path, "w", encoding="utf-8") as f:
        json.dump(prep, f, indent=2, ensure_ascii=False)

    report_path = os.path.join(out_dir, prep["report_file"])
    if not os.path.exists(report_path):
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(build_skeleton(report_date, reg, sources, meetings))

    print(f"Hot Topics prep for {prep['report_date']}")
    print(f"  window        : last {within} days")
    print(f"  web sources   : {len(sources)} enabled")
    print(f"  recent meets  : {len(meetings)} within window")
    for m in meetings:
        print(f"      - {m['committee']} {m['date']} ({m['doc_count']} docs)")
    dates = write_index()   # keep the website's date dropdown in sync

    print(f"  wrote         : {os.path.relpath(prep_path, PROJECT_ROOT)}")
    print(f"                  {os.path.relpath(report_path, PROJECT_ROOT)}")
    print(f"  index.json    : {len(dates)} report date(s)")
    print("\nNext: run the 'Hot Topics Generator' skill to fill the report from _prep.json.")


if __name__ == "__main__":
    main()
