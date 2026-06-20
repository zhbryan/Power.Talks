"""Generate per-committee meeting manifests for the Meeting Tracks group
homepage. Scans the ERCOT.STKHDR.MEETS document database and writes a
`_manifest.json` into each committee folder listing its meetings (date +
document filenames), newest first. The front-end fetches this at runtime to
render the group homepage's year-grouped meeting/document list.

Run after a download pass:
    python "Database Codes/download_STKHDR_Meets/gen_stkhdr_manifest.py"
"""

import os
import re
import json
from datetime import datetime

BASE = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.STKHDR.MEETS"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def committee_meetings(cdir):
    meetings = []
    for d in sorted(os.listdir(cdir), reverse=True):
        ddir = os.path.join(cdir, d)
        if not (os.path.isdir(ddir) and DATE_RE.match(d)):
            continue
        docs = sorted(
            f for f in os.listdir(ddir)
            if os.path.isfile(os.path.join(ddir, f))
            and not f.endswith(".tmp")
            and f != "_manifest.json"
        )
        meetings.append({"date": d, "doc_count": len(docs), "docs": docs})
    return meetings


def main():
    if not os.path.isdir(BASE):
        raise SystemExit(f"Base folder not found: {BASE}")

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    total_committees = total_meetings = total_docs = 0

    for abbrev in sorted(os.listdir(BASE)):
        cdir = os.path.join(BASE, abbrev)
        if not os.path.isdir(cdir):
            continue
        meetings = committee_meetings(cdir)
        manifest = {
            "committee": abbrev,
            "generated": ts,
            "meeting_count": len(meetings),
            "meetings": meetings,
        }
        with open(os.path.join(cdir, "_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        n_docs = sum(m["doc_count"] for m in meetings)
        total_committees += 1
        total_meetings += len(meetings)
        total_docs += n_docs
        print(f"  {abbrev:<10} {len(meetings):>4} meeting(s)  {n_docs:>6} doc(s)")

    print(f"\nWrote {total_committees} manifest(s): "
          f"{total_meetings} meetings, {total_docs} documents.")


if __name__ == "__main__":
    main()
