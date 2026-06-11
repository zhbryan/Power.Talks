"""
update_stale_profiles.py — One-off updater for profiles flagged stale on
2026-06-11 (post-downloader run + OneDrive NOGRR sync).

For each issue: appends timeline events for the new documents, sets
source_documents to the full current folder listing, and stamps
profile_last_updated. Status changes are handled separately (reports must
be read before changing status).
"""

import json
import os
import re
from datetime import datetime

BASE = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES"
DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx"}

# issue_id -> (category, [new documents to add to timeline])
WORK = {
    "NPRR1214": ("NPRR", ["1214NPRR-22-PRS-Ballot-061026.xls", "1214NPRR-23-PRS-Report-061026.docx"]),
    "NPRR1286": ("NPRR", ["1286NPRR-14-ROS-Ballot-060426.xls", "1286NPRR-15-ROS-Comments-060826.docx"]),
    "NPRR1335": ("NPRR", ["1335NPRR-04-PRS-Ballot-061026.xls", "1335NPRR-05-PRS-Report-061026.docx"]),
    "PGRR123": ("PGRR", ["123PGRR-08-ROS-Ballot-060426.xls", "123PGRR-09-ROS-Report-060426.docx"]),
    "PGRR128": ("PGRR", ["128PGRR-14-ROS-Ballot-060426.xls", "128PGRR-15-ROS-Report-060426.docx"]),
    "PGRR145": ("PGRR", ["145PGRR-117-Skybox-Datacenters-Comments-061026.docx"]),
    "PGRR146": ("PGRR", ["146PGRR-03-ROS-Ballot-060426.xls", "146PGRR-04-ROS-Report-060426.docx"]),
    "PGRR147": ("PGRR", ["147PGRR-02-ROS-Ballot-060426.xls", "147PGRR-03-ROS-Report-060426.docx"]),
    # NOGRR issues synced from OneDrive — include all files the sync added,
    # not just the ones the mtime fallback caught.
    "NOGRR273": ("NOGRR", [
        "273NOGRR-04-ERCOT-Comments-050626.docx", "273NOGRR-05-ROS-Ballot-050726.xls",
        "273NOGRR-06-ROS-Report-050726.docx", "273NOGRR-07-Impact-Analysis-052626.docx",
        "273NOGRR-08-ROS-Ballot-060426.xls", "273NOGRR-09-ROS-Report-060426.docx"]),
    "NOGRR281": ("NOGRR", [
        "281NOGRR-11-TAC-Ballot-051326.xls", "281NOGRR-12-TAC-Report-051326.docx",
        "281NOGRR-13-Board-Report-060226.docx"]),
    "NOGRR282": ("NOGRR", [
        "282NOGRR-26-TIEC-Comments-042426.docx", "282NOGRR-27-ERCOT-Comments-042426.docx",
        "282NOGRR-28-TAC-Ballot-042926.xls", "282NOGRR-29-TAC-Report-042926.docx",
        "282NOGRR-30-ERCOT-Comments-051126.docx", "282NOGRR-31-SB-Energy-Comments-051926.docx",
        "282NOGRR-32-TIEC-Comments-052126-v2.docx", "282NOGRR-33-Board-Report-060226.docx",
        "282NOGRR-34-Cipher-Digital-Comments-061126.docx"]),
    "NOGRR283": ("NOGRR", [
        "283NOGRR-09-TAC-Ballot-042926.xls", "283NOGRR-10-TAC-Report-042926.docx",
        "283NOGRR-11-Board-Report-060226.docx"]),
    "NOGRR286": ("NOGRR", [
        "286NOGRR-04-ROS-Ballot-050726.xls", "286NOGRR-05-ROS-Report-050726.docx",
        "286NOGRR-06-ERCOT-Comments-052726.doc", "286NOGRR-07-ROS-Ballot-060426.xls",
        "286NOGRR-08-ROS-Report-060426.docx"]),
}


def parse_doc(fname, issue_num, cat):
    """Return (date_iso, event, doc_label) from a document filename."""
    stem = os.path.splitext(fname)[0]
    m = re.search(r"-(\d{6})(?:-v\d+)?$", stem)
    date_iso = None
    if m:
        mm, dd, yy = m.group(1)[:2], m.group(1)[2:4], m.group(1)[4:]
        date_iso = f"20{yy}-{mm}-{dd}"
    # Strip "<n><CAT>-<seq>-" prefix and "-MMDDYY[-vN]" suffix.
    label = re.sub(rf"^{issue_num}{cat}-\d+-", "", stem)
    label = re.sub(r"-\d{6}(-v\d+)?$", "", label)
    event = label.replace("-", " ")
    return date_iso, event, stem


def main():
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for issue_id, (cat, new_docs) in WORK.items():
        num = re.search(r"\d+", issue_id).group(0)
        issue_dir = os.path.join(BASE, cat, issue_id)
        prof_path = os.path.join(issue_dir, "Quick runs", f"{issue_id} Profile.json")
        with open(prof_path, encoding="utf-8") as f:
            profile = json.load(f)

        timeline = profile.get("timeline") or []
        existing_docs = {str(e.get("doc", "")) for e in timeline}
        added = []
        for fname in new_docs:
            date_iso, event, stem = parse_doc(fname, num, cat)
            if any(stem in d or d in stem for d in existing_docs if d):
                continue
            timeline.append({"date": date_iso, "event": event, "doc": stem})
            added.append(f"{date_iso} {event}")
        timeline.sort(key=lambda e: (e.get("date") or ""))

        profile["timeline"] = timeline
        profile["source_documents"] = sorted(
            f for f in os.listdir(issue_dir)
            if os.path.isfile(os.path.join(issue_dir, f))
            and os.path.splitext(f)[1].lower() in DOC_EXTS
        )
        profile["profile_last_updated"] = now

        with open(prof_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"{issue_id} [{profile.get('status')}]: +{len(added)} timeline events")
        for a in added:
            print(f"    {a}")


if __name__ == "__main__":
    main()
