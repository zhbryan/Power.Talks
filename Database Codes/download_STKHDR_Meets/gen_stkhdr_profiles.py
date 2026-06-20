#!/usr/bin/env python3
"""Batch-generate ERCOT Stakeholder Meeting Profile JSONs for every meeting.

Implements the `ERCOT Stakeholder Meeting Profile` skill at scale: for each
committee/date folder under Documents Database/ERCOT.STKHDR.MEETS, write
<COMMITTEE>/<DATE>/Quick runs/<COMMITTEE>-<DATE> Profile.json.

Rules honored from the skill:
  - documents EXCLUDES .zip archives (case-insensitive), .tmp files, _manifest.json
  - group_summary carries leadership + voting_parties + voting_structure (per group)
  - empty arrays are [], unknown scalars are null
Existing profiles are left untouched (re-runnable; preserves curated ones).

Per-meeting extraction is best-effort:
  - agenda_items   from the *agenda* .docx (tables + numbered paragraphs)
  - ballot_results from the *ballot* .xls/.xlsx (motion lines; tallies left null)
  - working_group_reports inferred from report/update filenames
Old binary .doc agendas are not parsed (listed in documents only).
"""
import os, re, json, sys

ROOT = os.path.join("Documents Database", "ERCOT.STKHDR.MEETS")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ── ERCOT market segments (subcommittee/TAC voting) ──────────────────────────
SEG_SUB = [
    "Consumer (Residential / Commercial / Industrial subsegments)",
    "Cooperative", "Independent Generator", "Independent Power Marketer",
    "Independent Retail Electric Provider", "Investor Owned Utility", "Municipal",
]

# Working-group abbreviations used to detect WG reports in filenames.
WG_ABBRS = ["BSWG","DWG","IBRWG","MWG","NDSWG","OWG","OTWG","PDCWG","PLWG",
            "SPWG","SSWG","VPWG","CMWG","DSWG","SAWG","WMWG","TDTMS","RMTTF"]

# Agenda boilerplate to drop from key_discussion_topics.
TOPIC_SKIP = re.compile(r"antitrust|agenda review|adjourn|other business|"
                        r"approval of .*minutes|roll call|opening remarks", re.I)

# ── Committee metadata (leadership + voting model), from the Links skill §1 ───
# model: "board" (governance), "segment" (TAC + subcommittees), "wg" (advisory)
C = {
 "BOARD": ("Board of Directors", "Bill Flores", "Peggy Heeg", "board", None),
 "FA":    ("Finance and Audit Committee", "Christopher Krummel", None, "board", "Board"),
 "HRG":   ("HR and Governance Committee", "Peggy Heeg", None, "board", "Board"),
 "TS":    ("Technology and Security Committee", "John Swainson", None, "board", "Board"),
 "TAC":   ("Technical Advisory Committee", "Caitlin Smith", "Martha Henson", "segment", "Board"),
 "PRS":   ("Protocol Revision Subcommittee", None, None, "segment", "TAC"),
 "ROS":   ("Reliability and Operations Subcommittee", "Sandeep Borkar", "Shane Thomas", "segment", "TAC"),
 "RMS":   ("Retail Market Subcommittee", "John Schatz", "Debbie McKeever", "segment", "TAC"),
 "WMS":   ("Wholesale Market Subcommittee", None, None, "segment", "TAC"),
 "LLWG":  ("Large Load Working Group", "Bob Wittmeyer", "Patrick Gravois", "wg", "TAC"),
 "CFSG":  ("Credit Finance Sub Group", "Jett Price", "Loretto Martin", "wg", "TAC"),
 "RTCBTF":("Real-Time Co-optimization plus Batteries Task Force", None, None, "wg", "TAC"),
 "BESTF": ("Battery Energy Storage Task Force", None, None, "wg", "TAC"),
 "TDTMS": ("Texas Data Transport and MarkeTrak Systems Working Group", "Sheri Wiegand", "Rob Bevill / Monica Jones", "wg", "RMS"),
 "RMTTF": ("Retail Market Training Task Force", "Melinda Earnest / Tomas Fernandez / Deborah McKeever", None, "wg", "RMS"),
 "TXSET": ("Texas Standard Electronic Transaction (Texas SET) Working Group", None, None, "wg", "RMS"),
 "TXSETLP":("Texas SET Lite Process Working Group", None, None, "wg", "RMS"),
 "BSWG":  ("Black Start Working Group", "Michael Dieringer", "Cerina Rivera-Terrell", "wg", "ROS"),
 "DWG":   ("Dynamics Working Group", "Aditi Upadhyay", "Xuan Wu", "wg", "ROS"),
 "IBRWG": ("Inverter-Based Resource Working Group", "Julia Matevosyan", "Miguel Cova Acosta", "wg", "ROS"),
 "MWG":   ("Meter Working Group", "Kyle Stuckly", "Tony Davis", "wg", "ROS"),
 "NDSWG": ("Network Data Support Working Group", "Teddi Flessner", "Vincent Cutlip", "wg", "ROS"),
 "OWG":   ("Operations Working Group", None, None, "wg", "ROS"),
 "OTWG":  ("Operations Training Working Group", None, None, "wg", "ROS"),
 "PDCWG": ("Performance, Disturbance, Compliance Working Group", None, None, "wg", "ROS"),
 "PLWG":  ("Planning Working Group", "Mina Turner", "Kiran Kota", "wg", "ROS"),
 "SPWG":  ("System Protection Working Group", None, None, "wg", "ROS"),
 "SSWG":  ("Steady State Working Group", None, None, "wg", "ROS"),
 "VPWG":  ("Voltage Profile Working Group", None, None, "wg", "ROS"),
 "CMWG":  ("Congestion Management Working Group", None, None, "wg", "WMS"),
 "DSWG":  ("Demand Side Working Group", "Nathaniel Mancha", None, "wg", "WMS"),
 "SAWG":  ("Supply Analysis Working Group", "Kevin Hanson", "Pete Warnken / Greg Lackey", "wg", "WMS"),
 "WMWG":  ("Wholesale Market Working Group", "Amanda Frazier", "Trevor Safko", "wg", "WMS"),
}

CAL_SLUG = {  # calendar URL slug per committee (best-effort, base form)
 "BOARD":"Board-of-Directors-Meeting", "FA":"Finance-_-Audit-Committee",
 "HRG":"HR-_-Governance-Committee", "TS":"Technology-_-Security-Committee",
 "TAC":"TAC-Meeting", "TXSET":"Texas-SET_LP-Meeting", "TXSETLP":"Texas-SET_LP-Meeting",
}


def group_summary(abbr):
    full, chair, vc, model, parent = C.get(abbr, (abbr, None, None, "wg", "its parent committee"))
    lead_bits = []
    if chair: lead_bits.append(f"Chair: {chair}")
    if vc: lead_bits.append(f"Vice Chair: {vc}")
    leadership = "; ".join(lead_bits) if lead_bits else None

    if model == "board":
        if abbr == "BOARD":
            overview = ("The ERCOT Board of Directors is the governing body of ERCOT, "
                        "overseeing management, finance, and the reliability of the Texas grid.")
        else:
            overview = f"The {full} is a governance committee of the ERCOT Board of Directors."
        parties = ["ERCOT Board of Directors"]
        structure = ("Board governance voting — matters are decided by a majority of "
                     "directors. Not subject to ERCOT market-segment voting.")
    elif model == "segment":
        if abbr == "TAC":
            overview = ("The Technical Advisory Committee (TAC) is the senior stakeholder "
                        "committee reporting to the ERCOT Board, reviewing and forwarding "
                        "recommendations from the subcommittees (PRS, ROS, RMS, WMS).")
            structure = ("ERCOT market-segment voting at the TAC level — votes are tallied "
                         "by market segment, not headcount; recommendations are forwarded "
                         "to the ERCOT Board.")
        else:
            overview = (f"The {full} ({abbr}) reports to the Technical Advisory Committee "
                        f"(TAC) and develops and votes on revision requests and "
                        f"recommendations in its market domain.")
            structure = ("ERCOT market-segment voting: votes are tallied by market segment "
                         "(not headcount) and a typical motion passes on a majority of "
                         "segment votes. The Consumer segment carries 1.5 votes for "
                         "ROS/RMS/WMS (1 for PRS), split among present subsegments. "
                         "Endorsed items are forwarded to TAC.")
        parties = list(SEG_SUB)
    else:  # wg
        overview = (f"The {full} ({abbr}) is a technical working group under {parent}, "
                    f"developing analysis and recommendations in its subject area and "
                    f"reporting up to its parent committee.")
        parties = []
        structure = (f"Advisory working group — positions and straw votes are forwarded to "
                     f"{parent}; formal balloting occurs at the subcommittee/TAC level "
                     f"under ERCOT market-segment voting.")
    return full, chair, vc, {
        "overview": overview, "leadership": leadership,
        "voting_parties": parties, "voting_structure": structure,
    }


def extract_agenda(path):
    try:
        from docx import Document
        doc = Document(path)
    except Exception:
        return []
    items, seen = [], set()
    def add(t):
        t = re.sub(r"\s+", " ", t).strip()
        if t and t.lower() not in seen and len(t) < 200:
            seen.add(t.lower()); items.append(t)
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells]
            if cells and re.match(r"^\d+\.$", cells[0]):
                title = next((c for c in cells[1:] if c), "")
                if title and not re.match(r"^\d", title):
                    add(title)
    for p in doc.paragraphs:
        m = re.match(r"^\d+\.\s+(.+)", p.text.strip())
        if m:
            add(m.group(1))
    return items[:40]


def extract_ballot(path):
    txt = []
    try:
        if path.lower().endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(path, read_only=True, data_only=True)
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for v in row:
                        if isinstance(v, str) and v.strip():
                            txt.append(v.strip())
        else:  # .xls binary string extraction
            with open(path, "rb") as f:
                data = f.read()
            txt = [s.decode("ascii", "ignore")
                   for s in re.findall(rb"[\x20-\x7e]{6,}", data)]
    except Exception:
        return []
    motion_verb = re.compile(r"\bTo (approve|endorse|table|recommend|adopt|forward|"
                             r"accept|reject|remand|refer|amend)\b", re.I)
    rr = re.compile(r"^([A-Z]{2,7}\d{3,4})")
    out, seen = [], set()
    for line in txt:
        line = re.sub(r"[`^\x00-\x1f]+$", "", line).strip()
        if not (8 < len(line) < 300):
            continue
        if not (motion_verb.search(line) or rr.match(line)):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        m = rr.match(line)
        if m:
            item = m.group(1)
        elif "combined ballot" in line.lower():
            item = "Combined Ballot"
        elif "leadership" in line.lower() and " - " in line:
            item = line.split(" - ", 1)[0].strip()
        else:
            item = None
        motion = line.split(" - ", 1)[1].strip() if " - " in line else line
        out.append({"item": item, "motion": motion, "for": None,
                    "against": None, "abstain": None, "result": None})
        if len(out) >= 60:
            break
    return out


def wg_reports(files):
    found = []
    for f in files:
        low = f.lower()
        if not any(k in low for k in ("report", "update", "to-ros", "to_ros", "to-tac")):
            continue
        for wg in WG_ABBRS:
            if re.search(rf"\b{wg}\b", f, re.I) and wg not in found:
                found.append(wg)
    return found


def meeting_type(files):
    low = " ".join(files).lower()
    if "email" in low and "vote" in low:
        return "Email Vote"
    if "webex" in low:
        return "WebEx"
    return "Regular"


def build_profile(abbr, date, folder):
    files = sorted(f for f in os.listdir(folder)
                   if os.path.isfile(os.path.join(folder, f)))
    docs = [f for f in files
            if not f.lower().endswith((".zip", ".tmp")) and f != "_manifest.json"]

    agenda = []
    for f in docs:
        if "agenda" in f.lower() and f.lower().endswith(".docx"):
            agenda = extract_agenda(os.path.join(folder, f)); break
    ballots = []
    for f in docs:
        if "ballot" in f.lower() and f.lower().endswith((".xls", ".xlsx")):
            ballots = extract_ballot(os.path.join(folder, f)); break

    topics = [a for a in agenda if not TOPIC_SKIP.search(a)][:6]
    full, chair, vc, gsum = group_summary(abbr)
    mmddyyyy = date[5:7] + date[8:10] + date[0:4]
    slug = CAL_SLUG.get(abbr, f"{abbr}-Meeting")

    return {
        "committee": abbr,
        "committee_full_name": full,
        "meeting_date": date,
        "meeting_type": meeting_type(files),
        "calendar_url": f"https://www.ercot.com/calendar/{mmddyyyy}-{slug}",
        "chair": chair,
        "vice_chair": vc,
        "group_summary": gsum,
        "agenda_items": agenda,
        "ballot_results": ballots,
        "working_group_reports": wg_reports(docs),
        "key_discussion_topics": topics,
        "action_items": [],
        "documents": docs,
        "next_meeting_date": None,
    }


def main():
    overwrite = "--overwrite" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    written = skipped = errors = 0
    for abbr in sorted(os.listdir(ROOT)):
        if only and abbr not in only:
            continue
        cdir = os.path.join(ROOT, abbr)
        if not os.path.isdir(cdir):
            continue
        for date in sorted(d for d in os.listdir(cdir) if DATE_RE.match(d)):
            folder = os.path.join(cdir, date)
            if not os.path.isdir(folder):
                continue
            qr = os.path.join(folder, "Quick runs")
            out = os.path.join(qr, f"{abbr}-{date} Profile.json")
            if os.path.exists(out) and not overwrite:
                skipped += 1; continue
            try:
                prof = build_profile(abbr, date, folder)
                os.makedirs(qr, exist_ok=True)
                with open(out, "w", encoding="utf-8") as fh:
                    json.dump(prof, fh, indent=2, ensure_ascii=False)
                written += 1
                if written % 100 == 0:
                    print(f"  ... {written} written")
            except Exception as e:
                errors += 1
                print(f"  ERROR {abbr}/{date}: {e}")
    print(f"\nDone. written={written} skipped(existing)={skipped} errors={errors}")


if __name__ == "__main__":
    main()
