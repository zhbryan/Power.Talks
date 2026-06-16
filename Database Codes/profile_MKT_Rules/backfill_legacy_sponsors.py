"""
backfill_legacy_sponsors.py — One-off backfill of sponsor fields for legacy
profiles whose -01 submission document is an old binary .doc (or a .docx the
original extractor missed).

For every Profile.json with an empty sponsor_name, finds the issue's -01
document, extracts the Sponsor / Submitter's Information block (python-docx
for .docx, Word COM for .doc), and patches sponsor_name / sponsor_email /
sponsor_company / sponsor_phone / market_segment. Bumps profile_last_updated
so the summarizer scripts' ONLY_STALE mode rebuilds the affected summaries.

Issues with no -01 document on disk are skipped and counted.
"""

import glob
import json
import os
import re
from datetime import datetime

from docx import Document as DocxDoc
import win32com.client

BASE = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES"
CATEGORIES = ["NPRR", "NOGRR", "PGRR", "RMGRR", "SCR", "COPMGRR"]
NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

LABEL_MAP = {
    "name": "sponsor_name",
    "emailaddress": "sponsor_email",
    "email": "sponsor_email",
    "company": "sponsor_company",
    "phonenumber": "sponsor_phone",
    "phone": "sponsor_phone",
    "marketsegment": "market_segment",
}
ANCHOR = re.compile(r"sponsor|submitter", re.IGNORECASE)

_word = None


def get_word():
    global _word
    if _word is None:
        _word = win32com.client.Dispatch("Word.Application")
        _word.Visible = False
        _word.DisplayAlerts = 0
    return _word


def quit_word():
    global _word
    if _word is not None:
        try:
            _word.Quit()
        except Exception:
            pass
        _word = None


def rows_from_docx(path):
    doc = DocxDoc(path)
    rows = []
    for t in doc.tables:
        for row in t.rows:
            cells = [c.text.strip() for c in row.cells]
            rows.append(cells)
        rows.append(["__TABLE_BREAK__"])
    return rows


def rows_from_doc(path):
    word = get_word()
    d = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
    rows = []
    try:
        for t in d.Tables:
            try:
                n_rows = t.Rows.Count
                n_cols = t.Columns.Count
            except Exception:
                continue
            for r in range(1, n_rows + 1):
                cells = []
                for c in range(1, min(n_cols, 4) + 1):
                    try:
                        txt = t.Cell(r, c).Range.Text
                        cells.append(txt.replace("\r", " ").replace("\x07", "").strip())
                    except Exception:
                        continue
                if cells:
                    rows.append(cells)
            rows.append(["__TABLE_BREAK__"])
    finally:
        d.Close(False)
    return rows


def extract_sponsor(rows):
    """Find a Sponsor/Submitter anchor row, then harvest labeled rows after it."""
    out = {}
    anchor_idx = None
    for i, cells in enumerate(rows):
        joined = " ".join(cells[:2]).lower()
        if ANCHOR.search(joined) and len(joined) < 60:
            anchor_idx = i
            break
    if anchor_idx is None:
        return None
    for cells in rows[anchor_idx + 1: anchor_idx + 12]:
        if cells == ["__TABLE_BREAK__"]:
            if out.get("sponsor_name"):
                break
            continue
        if len(cells) < 2:
            continue
        key = re.sub(r"[^a-z]", "", cells[0].lower())
        field = LABEL_MAP.get(key)
        if field and cells[1].strip() and not out.get(field):
            out[field] = cells[1].strip()
        # Stop once we hit a new section after collecting a name
        if key in ("marketrulesstaffcontact", "comments") and out.get("sponsor_name"):
            break
    return out if out.get("sponsor_name") else None


# Matches the -01 sequence doc in both naming eras:
#   modern: 1329NPRR-01-Title-041326.docx
#   legacy: 104nprr_01_title.doc, 745scr_01retail_... (no separator after 01)
SEQ1 = re.compile(r"^\d+[a-z]+[-_ ]?0*1(?![0-9])", re.IGNORECASE)


def find_01_doc(issue_dir):
    cands = [
        os.path.join(issue_dir, f)
        for f in os.listdir(issue_dir)
        if os.path.splitext(f)[1].lower() in (".doc", ".docx") and SEQ1.match(f)
    ]
    return sorted(cands)[0] if cands else None


def main():
    fixed = no_doc = no_block = errors = 0
    try:
        for cat in CATEGORIES:
            for prof_path in sorted(glob.glob(os.path.join(BASE, cat, f"{cat}*", "Quick runs", "* Profile.json"))):
                try:
                    with open(prof_path, encoding="utf-8") as f:
                        profile = json.load(f)
                except (OSError, json.JSONDecodeError):
                    continue
                if profile.get("sponsor_name"):
                    continue
                issue_dir = os.path.dirname(os.path.dirname(prof_path))
                issue_id = os.path.basename(issue_dir)
                doc_path = find_01_doc(issue_dir)
                if not doc_path:
                    no_doc += 1
                    continue
                try:
                    if doc_path.lower().endswith(".docx"):
                        rows = rows_from_docx(doc_path)
                    else:
                        rows = rows_from_doc(doc_path)
                    sponsor = extract_sponsor(rows)
                except Exception as exc:
                    print(f"[ERR] {issue_id}: {exc}", flush=True)
                    errors += 1
                    continue
                if not sponsor:
                    no_block += 1
                    continue
                for k, v in sponsor.items():
                    if v and not profile.get(k):
                        profile[k] = v
                profile["profile_last_updated"] = NOW
                with open(prof_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2, ensure_ascii=False)
                fixed += 1
                print(f"[OK] {issue_id}: {sponsor.get('sponsor_name')}", flush=True)
    finally:
        quit_word()
    print(f"\nDone. fixed={fixed}, no -01 document={no_doc}, "
          f"no sponsor block found={no_block}, errors={errors}", flush=True)


if __name__ == "__main__":
    main()
