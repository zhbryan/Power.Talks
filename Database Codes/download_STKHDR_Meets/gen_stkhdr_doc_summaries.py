#!/usr/bin/env python3
"""Populate `document_reports` on every ERCOT stakeholder meeting Profile.json.

The Meeting Tracks counterpart of `gen_mkt_doc_summaries.py`: for each meeting
under Documents Database/ERCOT.STKHDR.MEETS/<COMMITTEE>/<YYYY-MM-DD>/, list the
documents the meeting published and write, into that meeting's Profile.json, a
`document_reports` array of

    { "file", "title", "agenda_item", "doc_type", "ext", "kind",
      "download_url", "executive_summary", "sponsor", "company" }

plus a meeting-level `meeting_time` when the calendar log knows the clock time.

The Meeting Tracks item page renders the entry for the clicked document (title +
executive summary + download link) and the right panel's "For the talk" card
reads sponsor / company / meeting / time from the same entry - one fetch, no
extra endpoint. See `Set Meeting Tracks Document Summary.md`.

Title, agenda item, document type and download URL are filename-derived, so
they are free and always present. The executive summary, sponsor and company
are read out of the document by Claude under `--ai`, which costs subscription
quota and is therefore paced:

    python "Database Codes/download_STKHDR_Meets/gen_stkhdr_doc_summaries.py"
    ...  BOARD                      # one committee
    ...  BOARD 2026-09-14 --ai      # one meeting, read the documents
    ...  --ai --budget 60           # paced backfill: at most 60 AI calls

Without `--ai` the three AI fields stay null and the UI shows "-". A document
that already has an executive summary is never re-read, so a budgeted run
resumes where the last one stopped. Exit code 2 means the run stopped on its
budget or an unavailable backend, with work still pending.
"""
import os
import re
import sys
import json
import glob
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(DB_DIR)
# Absolute, so the script works from any working directory - the relative ROOT
# in gen_mkt_doc_summaries.py only works when run from the project root.
ROOT = os.path.join(PROJECT_ROOT, "Documents Database", "ERCOT.STKHDR.MEETS")
WEB_BASE = "/Power.Talks/Documents%20Database/ERCOT.STKHDR.MEETS"
CAL_LOG = os.path.join(ROOT, "_calendar_log")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Documents whose text can be read for a summary.
READABLE_EXTS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".xlsm", ".ppt", ".pptx")
# Everything the group homepage lists gets an entry (so every clickable document
# has a title and a download link); only READABLE_EXTS are sent to the AI.
SKIP_SUFFIXES = (".zip", ".tmp", ".extracted", ".webm", ".mp3", ".mp4", ".log")

# Long forms first so the alternation prefers them. These are matched with a
# trailing \b and NEVER a trailing [a-z]* -- "mar" with a greedy letter suffix
# eats "Market", "dec" eats "Decision" and "may" eats "Mayor".
_MONTHS = ("january|february|march|april|june|july|august|september|october|"
           "november|december|jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|"
           "nov|dec")

# Document-type detection from the filename (first match wins, order matters).
DOC_TYPES = [
    ("Agenda",                  r"\bagenda\b"),
    ("Minutes",                 r"\bminutes\b"),
    ("Ballot",                  r"\bballot\b"),
    ("Segment Representatives", r"segment[_ -]?rep"),
    ("Impact Analysis",         r"impact[_ ]?analysis"),
    ("Revision Request",        r"revision[_ -]?request|\bnprr\d|\bnogrr\d|"
                                r"\bpgrr\d|\brmgrr\d|\bscr\d|\bcopmgrr\d"),
    ("Comments",                r"\bcomment"),
    ("Report",                  r"\breport\b|report[_ -]?to"),
    ("Update",                  r"\bupdate\b"),
    ("Presentation",            r"presentation|slides|overview|workshop|training"),
    ("Notice",                  r"\bnotice\b|announcement"),
    ("Charter",                 r"\bcharter\b|\bscope\b"),
]

EXT_KIND = {
    "pdf": "PDF document", "doc": "Word document", "docx": "Word document",
    "xls": "Excel workbook", "xlsx": "Excel workbook", "xlsm": "Excel workbook",
    "ppt": "PowerPoint deck", "pptx": "PowerPoint deck",
    "csv": "CSV data", "xml": "XML data", "html": "Web page", "msg": "Email",
    "txt": "Text file",
}


def detect_doc_type(name, ext):
    low = name.lower().replace("_", " ")   # '_' is a word char - break it for \b
    for label, pat in DOC_TYPES:
        if re.search(pat, low):
            return label
    if ext in ("ppt", "pptx"):
        return "Presentation"
    if ext in ("xls", "xlsx", "xlsm", "csv"):
        return "Workbook"
    return "Document"


def agenda_item(name):
    """The agenda number a meeting document is filed under: the leading '6.3' in
    '6.3-Industrial-Consumer-Segment-Google.pdf'. ERCOT numbers its meeting
    materials to the agenda, so this is the document's place in the meeting."""
    m = re.match(r"\s*(\d+(?:\.\d+)*)\s*[.\-_ ]", name)
    return m.group(1) if m else None


def clean_title(name):
    """Filename -> readable document title, e.g.
    '6.3-Industrial-Consumer-Segment-Google.pdf' ->
    'Industrial Consumer Segment Google'. Mirrors clean_doc_title() in
    gen_stkhdr_profiles.py; kept here so this script stands alone."""
    t = os.path.splitext(name)[0]
    t = re.sub(r"^\s*\d+(?:\.\d+)*[.\-_\s]+", "", t)          # agenda prefix
    t = re.sub(r"[_\-]+", " ", t)
    # A month name plus a day, or a two-day range: "September 14 15" and
    # "June 1 2" are whole date tokens. Stripping only one day number left the
    # other as the title's first word ("15 Board of Directors Agenda"). The
    # closing \b is what keeps "mar" from matching inside "Market".
    t = re.sub(r"\b(?:" + _MONTHS + r")\.?\s*\d{0,2}(?:\s*\d{1,2})?\b", "",
               t, flags=re.I)
    t = re.sub(r"\b\d{1,2}[ ./-]\d{1,2}[ ./-]\d{2,4}\b", "", t)
    t = re.sub(r"\b\d{6,8}\b", "", t)
    # A trailing/interior year is a date stamp ("...-Update-2026"); a LEADING
    # one is part of the title ("2027 ERCOT Methodologies for ...").
    t = re.sub(r"(?<=.)\b20\d{2}\b", "", t)
    # "public" and "draft" stay: they are part of real titles ("Notice of
    # Public Comment", "Draft Minutes"), not version noise.
    t = re.sub(r"\b(?:rev\s*\d+|v\d+|final|clean|redline)\b", "", t,
               flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -_.")
    return t or os.path.splitext(name)[0]


def doc_sort_key(name):
    """Agenda order: numeric on the leading number so 2 < 10, unnumbered last.
    The same ordering the manifest and the group homepage use."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)", name)
    if m:
        return (0, float(m.group(1)), name.lower())
    return (1, 0.0, name.lower())


def meeting_documents(folder):
    """-> [filename] for every document the group homepage lists, agenda order."""
    out = []
    for f in os.listdir(folder):
        if not os.path.isfile(os.path.join(folder, f)):
            continue
        low = f.lower()
        if low.endswith(SKIP_SUFFIXES) or low.endswith(".json"):
            continue
        out.append(f)
    return sorted(out, key=doc_sort_key)


def base_entry(committee, date, fname):
    ext = os.path.splitext(fname)[1].lower().lstrip(".")
    return {
        "file": fname,
        "title": clean_title(fname),
        "agenda_item": agenda_item(fname),
        "doc_type": detect_doc_type(fname, ext),
        "ext": ext,
        "kind": EXT_KIND.get(ext, (ext.upper() + " file") if ext else "Document"),
        "download_url": f"{WEB_BASE}/{quote(committee)}/{quote(date)}/{quote(fname)}",
        # Read out of the document by --ai.
        "executive_summary": None,
        "sponsor": None,
        "company": None,
    }


# -- meeting clock time, from the daily calendar log -------------------------
_cal_cache = None


def calendar_times():
    """-> {(COMMITTEE, YYYY-MM-DD): "9:30 AM"} from Documents Database/
    ERCOT.STKHDR.MEETS/_calendar_log/*.json.

    The log is a daily scrape that only started in November 2026, so it covers
    recent meetings and nothing historical - a miss is normal, not an error, and
    the card falls back to the meeting date alone. The committee is recovered
    from the calendar URL slug (.../11052026-ROS-Meeting), which carries the
    abbreviation ERCOT itself uses.
    """
    global _cal_cache
    if _cal_cache is not None:
        return _cal_cache
    _cal_cache = {}
    for path in glob.glob(os.path.join(CAL_LOG, "20??-??-??.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                day = json.load(fh)
        except Exception:
            continue
        for m in day.get("meetings") or []:
            t = (m.get("time") or "").strip()
            d = (m.get("date") or "").strip()
            if not t or not DATE_RE.match(d):
                continue
            slug = (m.get("url") or "").rsplit("/", 1)[-1]
            mm = re.match(r"\d{8}-([A-Za-z]+)", slug)
            abbr = (mm.group(1) if mm else "").upper()
            if "Board of Directors" in (m.get("title") or ""):
                abbr = "BOARD"
            if abbr:
                _cal_cache.setdefault((abbr, d), t)
    return _cal_cache


# -- AI per-document report (--ai) -------------------------------------------
AI_MODEL = "claude-opus-5-5"      # ai_backend maps this to --model opus; the
                                  # POWERTALKS_AI_MODEL env var overrides it.
AI_MAX_TOKENS = 900
STOP_AFTER_CONSEC_FAILS = 3
MAX_TEXT = 14000                  # same prompt size the MKT summarizer uses

_REPORT_KEYS = ("executive_summary", "sponsor", "company")
_SUMM_DIR = os.path.join(DB_DIR, "summarize_MKT_Rules")
_run_state = {"left": None, "stop": False}
_ai_usage = {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "fails": 0, "consec": 0}
_ai_client = None
_office = {"word": None, "word_n": 0, "ppt": None, "ppt_n": 0}
_OFFICE_RECYCLE = 40              # restart Word/PowerPoint every N opens


def _get_ai():
    global _ai_client
    if _ai_client is None:
        if _SUMM_DIR not in sys.path:
            sys.path.insert(0, _SUMM_DIR)
        import ai_backend
        _ai_client = ai_backend.get_client()
    return _ai_client


def _quit_office():
    for key in ("word", "ppt"):
        app = _office.get(key)
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        _office[key] = None
        _office[key + "_n"] = 0


def _office_app(key, progid):
    """A live Word/PowerPoint automation object, recycled every N opens -
    long-lived Office instances start truncating documents and leaking memory."""
    if _office[key] is not None and _office[key + "_n"] >= _OFFICE_RECYCLE:
        try:
            _office[key].Quit()
        except Exception:
            pass
        _office[key] = None
        _office[key + "_n"] = 0
    if _office[key] is None:
        import win32com.client
        _office[key] = win32com.client.Dispatch(progid)
        if key == "word":
            _office[key].Visible = False
        _office[key + "_n"] = 0
    _office[key + "_n"] += 1
    return _office[key]


def extract_text_any(path):
    """Best-effort plain text from a meeting document.

    Presentations matter here in a way they do not for market rules: .pptx and
    .ppt together are the largest document class in the stakeholder tree, so a
    reader that skipped them would leave most of the meeting record unread.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".docx":
            from docx import Document
            d = Document(path)
            parts = [p.text for p in d.paragraphs if p.text.strip()]
            for tbl in d.tables:
                for row in tbl.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells
                                            if c.text.strip()))
            return "\n".join(parts)
        if ext == ".pptx":
            from pptx import Presentation
            prs = Presentation(path)
            parts = []
            for i, slide in enumerate(prs.slides, 1):
                bits = []
                for shape in slide.shapes:
                    try:
                        if shape.has_text_frame and shape.text_frame.text.strip():
                            bits.append(shape.text_frame.text.strip())
                        elif getattr(shape, "has_table", False) and shape.has_table:
                            for row in shape.table.rows:
                                cells = [c.text.strip() for c in row.cells
                                         if c.text.strip()]
                                if cells:
                                    bits.append(" | ".join(cells))
                    except Exception:
                        pass
                if bits:
                    parts.append(f"[slide {i}] " + "\n".join(bits))
            return "\n".join(parts)
        if ext == ".pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        if ext == ".doc":
            word = _office_app("word", "Word.Application")
            doc = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
            try:
                return doc.Content.Text
            finally:
                doc.Close(False)
        if ext == ".ppt":
            app = _office_app("ppt", "PowerPoint.Application")
            # PowerPoint has no reliable invisible mode the way Word does;
            # WithWindow=False is what keeps it off the screen.
            pres = app.Presentations.Open(os.path.abspath(path), ReadOnly=True,
                                          WithWindow=False)
            try:
                parts = []
                for i in range(1, pres.Slides.Count + 1):
                    bits = []
                    for shape in pres.Slides(i).Shapes:
                        try:
                            if shape.HasTextFrame and shape.TextFrame.HasText:
                                bits.append(shape.TextFrame.TextRange.Text.strip())
                        except Exception:
                            pass
                    if bits:
                        parts.append(f"[slide {i}] " + "\n".join(bits))
                return "\n".join(parts)
            finally:
                pres.Close()
        if ext in (".xlsx", ".xlsm"):
            from openpyxl import load_workbook
            wb = load_workbook(path, read_only=True, data_only=True)
            rows = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    cells = [str(c).strip() for c in row
                             if c is not None and str(c).strip()]
                    if cells:
                        rows.append(" | ".join(cells))
            return "\n".join(rows)
        if ext == ".xls":
            import xlrd
            bk = xlrd.open_workbook(path)
            rows = []
            for sh in bk.sheets():
                for r in range(sh.nrows):
                    cells = [str(sh.cell_value(r, c)).strip()
                             for c in range(sh.ncols)
                             if str(sh.cell_value(r, c)).strip()]
                    if cells:
                        rows.append(" | ".join(cells))
            return "\n".join(rows)
    except Exception as e:
        print(f"    [READ-ERR] {os.path.basename(path)}: {e}")
    return ""


def ai_document_report(text, committee, full_name, date, entry):
    """Ask Claude for {executive_summary, sponsor, company} about ONE meeting
    document. Returns a dict over _REPORT_KEYS, or {} when nothing usable."""
    text = (text or "").strip()
    if len(text) < 40:
        return {}
    where = full_name or committee
    prompt = (
        f"You are reading ONE document published for an ERCOT stakeholder "
        f"meeting: {where} ({committee}), meeting of {date}.\n"
        f"Document file: {entry['file']}\n"
        f"Document type: {entry['doc_type']}"
        + (f"\nAgenda item: {entry['agenda_item']}"
           if entry.get("agenda_item") else "")
        + "\n\n"
        "Return a JSON object with exactly these keys, drawn from THIS "
        "document's text:\n"
        '- "executive_summary": a 2-4 sentence executive summary of this '
        "document for a reader who will not open it - what it covers, what it "
        "asks the committee to do or decide, and the numbers or outcomes that "
        "matter. Plain English, no bullet markers, at most 120 words - an "
        "agenda or a set of minutes covers many items, so summarize the "
        "meeting's shape rather than listing every one.\n"
        '- "sponsor": the person who authored or presented this document, as '
        "named in it (presenter, author, or the staff lead on the title "
        "slide/page). A person's name, not a committee.\n"
        '- "company": the organization that person speaks for (ERCOT, a market '
        "participant, a consultancy, the IMM, a law firm...).\n\n"
        "Use null for a field the document genuinely does not state - do not "
        "guess a presenter from the committee name. Do not invent facts. Plain "
        "text, no markdown. Return ONLY the JSON object.\n\n"
        f"DOCUMENT TEXT:\n{text[:MAX_TEXT]}"
    )
    try:
        msg = _get_ai().messages.create(
            model=AI_MODEL, max_tokens=AI_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}])
        _ai_usage["calls"] += 1
        _ai_usage["consec"] = 0
        _ai_usage["in"] += msg.usage.input_tokens
        _ai_usage["out"] += msg.usage.output_tokens
        _ai_usage["cost"] += getattr(msg.usage, "cost_usd", 0.0) or 0.0
        raw = msg.content[0].text.strip()
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: (data.get(k) or None) for k in _REPORT_KEYS}
    except Exception as e:
        _ai_usage["fails"] += 1
        _ai_usage["consec"] += 1
        print(f"    [AI-ERR] {entry['file']}: {e}")
        return {}


def build_document_reports(committee, full_name, date, folder, ai=False, prev=None):
    """-> [entry] for the meeting, carrying forward AI text already earned."""
    prev_by_file = {e.get("file"): e for e in (prev or []) if isinstance(e, dict)}
    out = []
    for fname in meeting_documents(folder):
        entry = base_entry(committee, date, fname)
        old = prev_by_file.get(fname) or {}
        for k in _REPORT_KEYS:
            if old.get(k):
                entry[k] = old[k]
        readable = fname.lower().endswith(READABLE_EXTS)
        if ai and readable and not (entry["executive_summary"] or "").strip():
            if _run_state["stop"]:
                pass                      # budget spent / backend unavailable
            elif _run_state["left"] is not None and _run_state["left"] <= 0:
                _run_state["stop"] = True
            else:
                rep = ai_document_report(
                    extract_text_any(os.path.join(folder, fname)),
                    committee, full_name, date, entry)
                if _run_state["left"] is not None:
                    _run_state["left"] -= 1
                for k in _REPORT_KEYS:
                    if rep.get(k):
                        entry[k] = rep[k]
                if rep:
                    print(f"    [AI] {fname}")
                if _ai_usage["consec"] >= STOP_AFTER_CONSEC_FAILS:
                    _run_state["stop"] = True
        out.append(entry)
    return out


def meeting_complete(prev, folder):
    """True when every readable document in the folder already has a summary."""
    if not prev or len(prev) != len(meeting_documents(folder)):
        return False
    return all((e.get("executive_summary") or "").strip() for e in prev
               if str(e.get("file", "")).lower().endswith(READABLE_EXTS))


def main():
    argv = sys.argv[1:]
    opt_values = set()
    if "--budget" in argv:
        i = argv.index("--budget") + 1
        _run_state["left"] = int(argv[i])
        opt_values.add(i)
    ai = "--ai" in argv
    force = "--force" in argv
    args = [a for i, a in enumerate(argv)
            if not a.startswith("--") and i not in opt_values]
    want_dates = {a for a in args if DATE_RE.match(a)}
    want_groups = {a.upper() for a in args if not DATE_RE.match(a)}

    times = calendar_times()
    updated = unchanged = skipped = errors = 0
    try:
        for abbr in sorted(os.listdir(ROOT)):
            if abbr.startswith(("_", ".")):
                continue
            if want_groups and abbr.upper() not in want_groups:
                continue
            cdir = os.path.join(ROOT, abbr)
            if not os.path.isdir(cdir):
                continue
            # Newest meeting first: the most recent record is the one anyone is
            # most likely to open, so a budgeted run fills that end first.
            for date in sorted((d for d in os.listdir(cdir) if DATE_RE.match(d)),
                               reverse=True):
                if want_dates and date not in want_dates:
                    continue
                folder = os.path.join(cdir, date)
                prof_path = os.path.join(folder, "Quick runs",
                                         f"{abbr}-{date} Profile.json")
                if not os.path.isfile(prof_path):
                    skipped += 1
                    continue
                try:
                    with open(prof_path, encoding="utf-8") as fh:
                        prof = json.load(fh)
                    prev = prof.get("document_reports") or []
                    # Resume is per DOCUMENT: a meeting is skipped only when
                    # every readable document already carries its summary.
                    if ai and not force and meeting_complete(prev, folder):
                        skipped += 1
                        continue
                    if ai:
                        print(f"  {abbr} {date} ...")
                    reports = build_document_reports(
                        abbr, prof.get("committee_full_name"), date, folder,
                        ai=ai, prev=prev)
                    mtime = times.get((abbr.upper(), date))
                    if reports == prev and prof.get("meeting_time", "?") == mtime:
                        unchanged += 1
                        continue
                    # Only these two fields are touched; the rest of the profile
                    # (written by gen_stkhdr_profiles.py) is left exactly as is.
                    prof["document_reports"] = reports
                    prof["meeting_time"] = mtime
                    with open(prof_path, "w", encoding="utf-8") as fh:
                        json.dump(prof, fh, indent=2, ensure_ascii=False)
                    updated += 1
                    if not ai and updated % 200 == 0:
                        print(f"  ... {updated} meetings updated")
                except Exception as e:
                    errors += 1
                    print(f"  ERROR {abbr}/{date}: {e}")
                if _run_state["stop"]:
                    print("  [stop] AI budget spent or backend unavailable after "
                          f"{_ai_usage['calls']} call(s); the remaining documents "
                          "keep their blanks and are picked up by the next run.")
                    break
            if _run_state["stop"]:
                break
    finally:
        _quit_office()

    print(f"\nDone. meetings updated={updated}, unchanged={unchanged}, "
          f"skipped={skipped} (no profile, or already complete), errors={errors}")
    if _ai_usage["calls"]:
        print(f"AI: {_ai_usage['calls']} call(s), in={_ai_usage['in']} "
              f"out={_ai_usage['out']} tokens, "
              f"${_ai_usage['cost']:.4f} list-equivalent ({AI_MODEL}), "
              f"{_ai_usage['fails']} failure(s)")
    return 2 if _run_state["stop"] else 0


if __name__ == "__main__":
    sys.exit(main())
