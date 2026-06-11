"""
find_stale_profiles.py — Detect ERCOT market rules issues whose profile JSON
is missing or out of date relative to the documents in the issue folder.

Used by the "ERCOT Market Rules Profile" skill (Update Mode).

Detection rules, per issue folder under BASE/<CATEGORY>/<ISSUE_ID>/:
  - No "Quick runs/<ISSUE_ID> Profile.json"            -> reported as "missing"
  - Profile has "source_documents": docs in the folder
    not listed there                                   -> reported as "stale"
  - Legacy profile without "source_documents": docs
    with mtime newer than the profile file's mtime     -> reported as "stale"

Output: JSON to stdout —
  {"missing": [...], "stale": [...], "checked": N}
Each entry: {"category", "issue_id", "new_documents": [...]}
"""

import json
import os
import sys

BASE = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES"
DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}


def issue_documents(issue_dir):
    """Document filenames directly inside the issue folder."""
    return sorted(
        f for f in os.listdir(issue_dir)
        if os.path.isfile(os.path.join(issue_dir, f))
        and os.path.splitext(f)[1].lower() in DOC_EXTS
    )


def main():
    missing, stale = [], []
    checked = 0

    for cat in sorted(os.listdir(BASE)):
        cat_dir = os.path.join(BASE, cat)
        if not os.path.isdir(cat_dir):
            continue
        for issue in sorted(os.listdir(cat_dir)):
            issue_dir = os.path.join(cat_dir, issue)
            if not os.path.isdir(issue_dir):
                continue
            docs = issue_documents(issue_dir)
            if not docs:
                continue
            checked += 1

            profile_path = os.path.join(issue_dir, "Quick runs", f"{issue} Profile.json")
            if not os.path.exists(profile_path):
                missing.append({"category": cat, "issue_id": issue, "new_documents": docs})
                continue

            try:
                with open(profile_path, encoding="utf-8") as f:
                    profile = json.load(f)
            except (OSError, json.JSONDecodeError):
                profile = {}

            sources = profile.get("source_documents")
            if isinstance(sources, list):
                new_docs = sorted(set(docs) - set(sources))
            else:
                profile_mtime = os.path.getmtime(profile_path)
                new_docs = [
                    f for f in docs
                    if os.path.getmtime(os.path.join(issue_dir, f)) > profile_mtime
                ]
            if new_docs:
                stale.append({"category": cat, "issue_id": issue, "new_documents": new_docs})

    json.dump({"missing": missing, "stale": stale, "checked": checked},
              sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
