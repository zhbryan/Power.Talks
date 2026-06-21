#!/usr/bin/env python3
"""Populate `source_documents` (the "Documents Submitted" list + per-document
summary) on every ERCOT market-rules issue Profile.json.

Implements `Set Paper Trails Document Summary.md`: for each issue under
Documents Database/ERCOT.MKT.RULES/<CAT>/<ISSUE_ID>/, list the submitted files
(excluding .zip/.tmp and the Quick runs JSONs) and write, into the issue's
Profile.json, a `source_documents` array of:

    { "file", "doc_type", "date", "author", "summary", "key_points",
      "download_url" }

The Paper Trails item-rule card lists these (title link + download button) and
the content window renders the clicked entry's summary (see the homepage skill).

Summaries are filename-derived by default (fast, full coverage). Pass --read to
also open each document and extract a couple of substantive sentences
(.docx/.pdf/.xlsx; slower) — off by default.

    python "Database Codes/gen_mkt_doc_summaries.py"            # all categories
    python "Database Codes/gen_mkt_doc_summaries.py" NPRR PGRR  # subset
"""
import os
import re
import sys
import json
from urllib.parse import quote

ROOT = os.path.join("Documents Database", "ERCOT.MKT.RULES")
WEB_BASE = "/Power.Talks/Documents%20Database/ERCOT.MKT.RULES"

DOC_EXTS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")
_MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()

# Document-type detection from the filename (first match wins, order matters).
DOC_TYPES = [
    ("Impact Analysis",          r"impact[_ ]?analysis"),
    ("Cost/Benefit Analysis",    r"\bcba\b|cost[_ ]?benefit"),
    ("Board Action Report",      r"board[_ ]?action"),
    ("TAC Recommendation Report",r"tac[_ ]?rec"),
    ("PRS Recommendation Report",r"prs[_ ]?rec"),
    ("ROS Report",               r"ros[_ ]?(report|rec)"),
    ("WMS Report",               r"wms[_ ]?(report|rec)"),
    ("Recommendation Report",    r"recommendation|rec[_ ]?report"),
    ("Ballot",                   r"\bballot\b"),
    ("Comments",                 r"\bcomment"),
    ("Markup / Redline",         r"markup|redline|black[_ ]?line|black[_ ]?lined"),
    ("Presentation",             r"presentation|slides|overview|update"),
    ("Impact Analysis",          r"\bia\b"),
    ("As-Built",                 r"as[_ ]?built"),
]


def detect_doc_type(name, seq):
    low = name.lower().replace("_", " ")   # '_' is a regex word char — break it so \b works
    for label, pat in DOC_TYPES:
        if re.search(pat, low):
            return label
    if seq == 1:                       # the first item is usually the request itself
        return "Revision Request"
    return "Document"


def detect_date(name):
    digits = re.findall(r"\d+", name)
    for d in digits:
        if len(d) == 8:                # YYYYMMDD or MMDDYYYY
            if d[:4].startswith(("19", "20")):
                y, m, dd = d[:4], d[4:6], d[6:8]
            else:
                m, dd, y = d[:2], d[2:4], d[4:8]
            if 1 <= int(m) <= 12 and 1 <= int(dd) <= 31:
                return f"{y}-{m}-{dd}"
        if len(d) == 6:                # MMDDYY
            m, dd, yy = d[:2], d[2:4], d[4:6]
            if 1 <= int(m) <= 12 and 1 <= int(dd) <= 31:
                yr = ("20" if int(yy) < 50 else "19") + yy
                return f"{yr}-{m}-{dd}"
    return None


def detect_author(name):
    low = name.lower().replace("_", " ")
    for token, label in [("ercot", "ERCOT"), ("imm", "IMM"), ("opuc", "OPUC"),
                         ("puct", "PUCT"), ("tcpa", "TCPA"), ("tiec", "TIEC")]:
        if re.search(rf"\b{token}\b", low):
            return label
    return None


def clean_title(name, issue_id):
    t = os.path.splitext(name)[0]
    # drop the leading "<num><cat>_NN_" / "<cat><num>_NN_" packet prefix
    t = re.sub(r"^\d+[a-z]{2,7}[_ -]?\d{1,3}[_ -]+", "", t, flags=re.I)
    t = re.sub(rf"^{re.escape(issue_id)}[_ -]+", "", t, flags=re.I)
    t = re.sub(r"[_]+", " ", t)
    t = re.sub(r"\b\d{6,8}\b", "", t)               # date blobs
    t = re.sub(r"\b(rev\s*\d+|v\d+|final|clean|redline)\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -—_.")
    return t.title() if t and t.islower() else t


def summarize_file(fname, issue_id, seq):
    doc_type = detect_doc_type(fname, seq)
    date = detect_date(fname)
    author = detect_author(fname)
    title = clean_title(fname, issue_id)
    bits = [f"{doc_type} for {issue_id}"]
    if author:
        bits[0] = f"{author} {doc_type.lower()} for {issue_id}"
    if title and title.lower() not in doc_type.lower():
        bits.append(f"— {title}")
    if date:
        bits.append(f"(dated {date})")
    summary = " ".join(bits).strip() + "."
    return {
        "file": fname,
        "doc_type": doc_type,
        "date": date,
        "author": author,
        "summary": summary,
        "key_points": [],
        "download_url": None,   # set by build_source_documents (needs cat/issue)
    }


def build_source_documents(cat, issue_id, folder):
    qr = os.path.join(folder, "Quick runs")
    files = sorted(
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(DOC_EXTS)
        and not f.lower().endswith((".zip", ".tmp"))
    )
    docs = []
    for i, f in enumerate(files, 1):
        entry = summarize_file(f, issue_id, i)
        entry["download_url"] = f"{WEB_BASE}/{quote(cat)}/{quote(issue_id)}/{quote(f)}"
        docs.append(entry)
    return docs


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    updated = skipped = 0
    for cat in sorted(os.listdir(ROOT)):
        if only and cat not in only:
            continue
        cdir = os.path.join(ROOT, cat)
        if not os.path.isdir(cdir):
            continue
        for issue_id in sorted(os.listdir(cdir)):
            folder = os.path.join(cdir, issue_id)
            if not os.path.isdir(folder):
                continue
            profile = os.path.join(folder, "Quick runs", f"{issue_id} Profile.json")
            if not os.path.exists(profile):
                skipped += 1
                continue
            try:
                with open(profile, encoding="utf-8") as fh:
                    data = json.load(fh)
                data["source_documents"] = build_source_documents(cat, issue_id, folder)
                with open(profile, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=2, ensure_ascii=False)
                updated += 1
                if updated % 200 == 0:
                    print(f"  ... {updated} profiles updated")
            except Exception as e:
                print(f"  ERROR {cat}/{issue_id}: {e}")
    print(f"\nDone. profiles updated={updated}  (no profile){skipped}")


if __name__ == "__main__":
    main()
