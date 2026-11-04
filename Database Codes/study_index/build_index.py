#!/usr/bin/env python3
"""build_index.py — Build the Power.Talks study index (Tier 1 + Tier 2).

Indexes the *derived* knowledge layer the nightly routine already produces —
not the 22 GB of raw source documents — into one SQLite file with FTS5:

  Tier 1  structured tables for exact, *complete* answers
            issues / issue_sections / issue_timeline / documents
            meetings / meeting_documents / terms
  Tier 2  FTS5 (BM25) full-text tables for topic discovery
            issues_fts / docs_fts / meetings_fts

Sources (all written by the existing pipeline):
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ID>/Quick runs/<ID> Profile.json
  Documents Database/ERCOT.MKT.RULES/<CAT>/<ID>/Quick runs/<ID> Summary.json
  Documents Database/ERCOT.STKHDR.MEETS/<CMTE>/<DATE>/Quick runs/<..> Profile.json
  Database Codes/reference_info/ercot_glossary.json
  Database Codes/reference_info/ercot_market_keywords.json

Output:
  Database Codes/study_index/study_index.db

The build is a full rebuild into a temporary file that then replaces the live
database, so a run is idempotent and never leaves a half-built index behind.
It reads only small JSON files, so a full rebuild is seconds, not minutes.

Usage:
    py -3 "Database Codes/study_index/build_index.py"
    py -3 "Database Codes/study_index/build_index.py" --quiet
    py -3 "Database Codes/study_index/build_index.py" --out other.db
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time

# --- Paths ------------------------------------------------------------------
HERE         = os.path.dirname(os.path.abspath(__file__))
DB_CODES     = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(DB_CODES)
DOCS_DB      = os.path.join(PROJECT_ROOT, "Documents Database")
MKT_ROOT     = os.path.join(DOCS_DB, "ERCOT.MKT.RULES")
STK_ROOT     = os.path.join(DOCS_DB, "ERCOT.STKHDR.MEETS")
REF_INFO     = os.path.join(DB_CODES, "reference_info")
DEFAULT_DB   = os.path.join(HERE, "study_index.db")

QUIET = False


def log(msg):
    if not QUIET:
        print(msg, flush=True)


# --- Helpers ----------------------------------------------------------------
def read_json(path):
    """Load a JSON file, tolerating the mojibake some summaries carry."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except Exception as e:
        log("    ! unreadable %s: %s" % (os.path.relpath(path, PROJECT_ROOT), e))
        return None


def as_text(value):
    """Flatten any profile/summary value into searchable plain text.

    The six category profilers and the meeting profiler do not agree on whether
    a field is a string, a list of strings, or a list of dicts, and the shapes
    drift as the skills evolve. Recursive flattening keeps the index working
    across all of them instead of breaking on the next schema change.
    """
    if value is None or value is False:
        return ""
    if value is True:
        return "true"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(t for t in (as_text(v) for v in value.values()) if t)
    if isinstance(value, (list, tuple)):
        return " ".join(t for t in (as_text(v) for v in value) if t)
    return str(value)


def scalar(value):
    """A value destined for a Tier 1 column: keep scalars, flatten the rest."""
    if value is None or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value.strip() or None
    return as_text(value) or None


def flatten_strings(value):
    """Yield one string per leaf - for the one-row-per-item Tier 1 child tables."""
    if value is None:
        return
    if isinstance(value, str):
        v = value.strip()
        if v:
            yield v
    elif isinstance(value, (int, float)):
        yield str(value)
    elif isinstance(value, dict):
        # A section entry is often {"section": "25.1", "description": ...}
        for key in ("section", "name", "title", "document", "doc", "id"):
            if isinstance(value.get(key), str) and value[key].strip():
                yield value[key].strip()
                return
        text = as_text(value)
        if text:
            yield text
    elif isinstance(value, (list, tuple)):
        for item in value:
            for leaf in flatten_strings(item):
                yield leaf


MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
for _full, _i in list(MONTHS.items()):
    MONTHS[_full[:3]] = _i


def norm_date(value):
    """Normalise a profile date to ISO ``YYYY-MM-DD``, or None.

    Most profiles already carry ISO dates, but a handful record free text the
    source document used verbatim ("April 30,2014", "14 May 2002",
    "October 12 , 2016", "Unknown"). Date filtering and the chronology a study
    brief is built on are only sound if every date sorts the same way, so the
    conversion happens here, once, instead of in every caller.
    """
    text = scalar(value)
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text or text.lower() in ("unknown", "n/a", "na", "tbd", "none"):
        return None

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        y, mo, d = (int(g) for g in m.groups())
    else:
        # "April 30,2014" / "October 12 , 2016" / "Apr 30 2014"
        m = re.match(r"^([A-Za-z]{3,9})\s*\.?\s+(\d{1,2})\s*,?\s*(\d{4})$", text)
        if m and m.group(1).lower() in MONTHS:
            mo, d, y = MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
        else:
            # "14 May 2002"
            m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9})\s*\.?\s*,?\s*(\d{4})$", text)
            if m and m.group(2).lower() in MONTHS:
                d, mo, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
            else:
                # "01/14/2008" / "1-14-08"
                m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", text)
                if not m:
                    return None
                mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if y < 100:
                    y += 2000 if y < 70 else 1900

    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return "%04d-%02d-%02d" % (y, mo, d)


SECTION_NUM_RE = re.compile(r"\b\d{1,2}(?:\.\d{1,3}){1,5}\b")


def section_numbers(text):
    """Pull every section *number* out of a recorded section string.

    The profilers record sections however the source document phrased them: a
    bare number ("2.1"), a title ("Definitions"), or several of both run
    together ("3.14.3.1 Emergency Response Service Procurement 3.14.3.3 ..."). A
    "every issue touching section X" query is only complete if those buried
    numbers are indexed individually, so each one becomes its own row.
    """
    text = (text or "").strip()
    if not text:
        return []
    # A string that is nothing but a section reference ("2", "6.5.7.3").
    if re.fullmatch(r"\d{1,2}(?:\.\d{1,3})*", text):
        return [text]
    # Otherwise only dotted numbers, so "75 MW" or "Form S" contribute nothing.
    return list(dict.fromkeys(m.group(0) for m in SECTION_NUM_RE.finditer(text)))


def first(mapping, *keys):
    """First present, non-empty value among `keys` - absorbs per-category naming."""
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if mapping.get(key) not in (None, "", [], {}):
            return mapping[key]
    return None


# --- Schema -----------------------------------------------------------------
TOKENIZE = "unicode61 remove_diacritics 2"

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

-- Tier 1: structured ------------------------------------------------------
CREATE TABLE issues (
    uid                  INTEGER PRIMARY KEY,
    category             TEXT NOT NULL,
    issue_id             TEXT NOT NULL UNIQUE,
    issue_number         INTEGER,
    title                TEXT,
    status               TEXT,
    date_posted          TEXT,   -- normalised to ISO YYYY-MM-DD
    date_posted_raw      TEXT,   -- as the profile recorded it
    effective_date       TEXT,
    requested_resolution TEXT,
    sponsor_name         TEXT,
    sponsor_email        TEXT,
    sponsor_company      TEXT,
    market_segment       TEXT,
    revision_description TEXT,
    business_case        TEXT,
    executive_summary    TEXT,
    current_status       TEXT,
    doc_count            INTEGER DEFAULT 0,
    summary_last_updated TEXT,
    profile_path         TEXT,
    summary_path         TEXT
);
CREATE INDEX idx_issues_cat    ON issues(category);
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_posted ON issues(date_posted);

CREATE TABLE issue_sections (
    issue_uid   INTEGER NOT NULL REFERENCES issues(uid),
    section     TEXT NOT NULL,  -- as recorded, title and all
    section_num TEXT            -- one extracted number, NULL for a pure title
);
CREATE INDEX idx_sections_sec ON issue_sections(section);
CREATE INDEX idx_sections_num ON issue_sections(section_num);
CREATE INDEX idx_sections_uid ON issue_sections(issue_uid);

CREATE TABLE issue_related_docs (
    issue_uid INTEGER NOT NULL REFERENCES issues(uid),
    document  TEXT NOT NULL
);
CREATE INDEX idx_related_uid ON issue_related_docs(issue_uid);

CREATE TABLE issue_timeline (
    issue_uid INTEGER NOT NULL REFERENCES issues(uid),
    date      TEXT,   -- normalised to ISO YYYY-MM-DD
    date_raw  TEXT,
    event     TEXT,
    doc       TEXT
);
CREATE INDEX idx_timeline_uid  ON issue_timeline(issue_uid);
CREATE INDEX idx_timeline_date ON issue_timeline(date);

CREATE TABLE documents (
    uid          INTEGER PRIMARY KEY,
    issue_uid    INTEGER NOT NULL REFERENCES issues(uid),
    issue_id     TEXT NOT NULL,
    file         TEXT,
    title        TEXT,
    doc_type     TEXT,
    date         TEXT,
    date_posted  TEXT,
    author       TEXT,
    submitter    TEXT,
    download_url TEXT
);
CREATE INDEX idx_docs_issue ON documents(issue_uid);
CREATE INDEX idx_docs_type  ON documents(doc_type);
CREATE INDEX idx_docs_date  ON documents(date);

CREATE TABLE meetings (
    uid                 INTEGER PRIMARY KEY,
    committee           TEXT NOT NULL,
    committee_full_name TEXT,
    meeting_date        TEXT,
    meeting_type        TEXT,
    calendar_url        TEXT,
    chair               TEXT,
    vice_chair          TEXT,
    next_meeting_date   TEXT,
    doc_count           INTEGER DEFAULT 0,
    profile_path        TEXT
);
CREATE INDEX idx_meet_cmte ON meetings(committee);
CREATE INDEX idx_meet_date ON meetings(meeting_date);

CREATE TABLE meeting_documents (
    meeting_uid  INTEGER NOT NULL REFERENCES meetings(uid),
    committee    TEXT,
    meeting_date TEXT,
    file         TEXT
);
CREATE INDEX idx_mdocs_uid ON meeting_documents(meeting_uid);

CREATE TABLE terms (
    term        TEXT NOT NULL,
    acronym     TEXT,
    category    TEXT,
    description TEXT,
    source      TEXT NOT NULL,
    trending    INTEGER DEFAULT 0
);
CREATE INDEX idx_terms_term ON terms(term);
CREATE INDEX idx_terms_acro ON terms(acronym);

-- Tier 2: FTS5 (rowid == the Tier 1 uid) ----------------------------------
CREATE VIRTUAL TABLE issues_fts USING fts5(
    issue_id, title, revision_description, reason_for_revision, business_case,
    executive_summary, background, key_change, impacts_summary, current_status,
    stakeholder_key_debates, ercot_opinion, imm_opinion, sections,
    tokenize="__TOK__"
);

CREATE VIRTUAL TABLE docs_fts USING fts5(
    issue_id, file, doc_type, title, summary, description,
    justification, detailed_background, key_points,
    tokenize="__TOK__"
);

CREATE VIRTUAL TABLE meetings_fts USING fts5(
    committee, committee_full_name, meeting_date, overview, voting_structure,
    topics, debates, voting_outcomes, key_discussion_topics, action_items,
    agenda_items, working_group_reports, ballot_results, documents,
    tokenize="__TOK__"
);
""".replace("__TOK__", TOKENIZE)

ISSUES_FTS_COLS = (
    "issue_id, title, revision_description, reason_for_revision, business_case, "
    "executive_summary, background, key_change, impacts_summary, current_status, "
    "stakeholder_key_debates, ercot_opinion, imm_opinion, sections"
)
DOCS_FTS_COLS = (
    "issue_id, file, doc_type, title, summary, description, "
    "justification, detailed_background, key_points"
)
MEETINGS_FTS_COLS = (
    "committee, committee_full_name, meeting_date, overview, voting_structure, "
    "topics, debates, voting_outcomes, key_discussion_topics, action_items, "
    "agenda_items, working_group_reports, ballot_results, documents"
)


def fts_insert(table, cols):
    """INSERT statement for an FTS5 table, with rowid bound to the Tier 1 uid."""
    n = len(cols.split(",")) + 1
    return "INSERT INTO %s (rowid, %s) VALUES (%s)" % (
        table, cols, ",".join("?" * n))


# --- Market rules -----------------------------------------------------------
def iter_issue_profiles():
    """Yield (category, issue_id, profile_path) for every market-rules profile."""
    if not os.path.isdir(MKT_ROOT):
        return
    for category in sorted(os.listdir(MKT_ROOT)):
        cat_dir = os.path.join(MKT_ROOT, category)
        if not os.path.isdir(cat_dir):
            continue
        for issue_id in sorted(os.listdir(cat_dir)):
            quick = os.path.join(cat_dir, issue_id, "Quick runs")
            if not os.path.isdir(quick):
                continue
            profile = os.path.join(quick, "%s Profile.json" % issue_id)
            if os.path.isfile(profile):
                yield category, issue_id, profile


def index_market_rules(conn):
    sql_issue = """INSERT INTO issues (uid, category, issue_id, issue_number,
            title, status, date_posted, date_posted_raw, effective_date,
            requested_resolution,
            sponsor_name, sponsor_email, sponsor_company, market_segment,
            revision_description, business_case, executive_summary,
            current_status, doc_count, summary_last_updated,
            profile_path, summary_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    sql_doc = """INSERT INTO documents (uid, issue_uid, issue_id, file, title,
            doc_type, date, date_posted, author, submitter, download_url)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
    sql_issue_fts = fts_insert("issues_fts", ISSUES_FTS_COLS)
    sql_doc_fts = fts_insert("docs_fts", DOCS_FTS_COLS)

    uid = doc_uid = n_summaries = 0

    for category, issue_id, profile_path in iter_issue_profiles():
        prof = read_json(profile_path)
        if not isinstance(prof, dict):
            continue
        uid += 1

        summary_path = os.path.join(os.path.dirname(profile_path),
                                    "%s Summary.json" % issue_id)
        summ = read_json(summary_path) if os.path.isfile(summary_path) else None
        if isinstance(summ, dict):
            n_summaries += 1
        else:
            summ = {}

        source_docs = prof.get("source_documents")
        if not isinstance(source_docs, list):
            source_docs = []

        exec_summary = as_text(first(summ, "executive_summary"))
        cur_status = as_text(first(summ, "current_status", "status_narrative"))
        posted_raw = (scalar(first(prof, "date_posted_decision", "date_posted"))
                      or scalar(first(summ, "date_posted")))

        conn.execute(sql_issue, (
            uid,
            scalar(prof.get("category")) or category,
            issue_id,
            first(prof, "issue_number", "nprr_number"),
            scalar(first(prof, "title")) or scalar(first(summ, "title")),
            scalar(first(prof, "status")) or scalar(first(summ, "status")),
            norm_date(posted_raw),
            posted_raw,
            norm_date(first(prof, "effective_date")
                      or first(summ, "effective_date")),
            scalar(first(prof, "timeline_requested_resolution")),
            scalar(first(prof, "sponsor_name")) or scalar(first(summ, "sponsor")),
            scalar(first(prof, "sponsor_email")),
            scalar(first(prof, "sponsor_company")),
            scalar(first(prof, "market_segment")),
            scalar(first(prof, "revision_description")),
            scalar(first(prof, "business_case")),
            exec_summary or None,
            cur_status or None,
            len(source_docs),
            scalar(first(summ, "summary_last_updated")),
            os.path.relpath(profile_path, PROJECT_ROOT),
            os.path.relpath(summary_path, PROJECT_ROOT) if summ else None))

        # Sections come from the profile (governing document) and the summary
        # (protocol sections); both feed "every issue touching section X".
        sections = set()
        for key in ("governing_document_sections", "protocol_sections",
                    "affected_sections"):
            sections.update(flatten_strings(prof.get(key)))
            sections.update(flatten_strings(summ.get(key)))
        if sections:
            section_rows = []
            for raw in sorted(sections):
                nums = section_numbers(raw)
                if nums:
                    section_rows.extend((uid, raw, n) for n in nums)
                else:
                    section_rows.append((uid, raw, None))
            conn.executemany("INSERT INTO issue_sections VALUES (?,?,?)",
                             section_rows)

        related = sorted(set(flatten_strings(
            prof.get("related_documents_requiring_revision"))))
        if related:
            conn.executemany("INSERT INTO issue_related_docs VALUES (?,?)",
                             [(uid, d) for d in related])

        timeline = prof.get("timeline") or summ.get("timeline") or []
        rows = []
        if isinstance(timeline, list):
            for entry in timeline:
                if isinstance(entry, dict):
                    raw = scalar(entry.get("date"))
                    rows.append((uid, norm_date(raw), raw,
                                 scalar(first(entry, "event", "milestone")),
                                 scalar(first(entry, "doc", "document"))))
                elif as_text(entry):
                    rows.append((uid, None, None, as_text(entry), None))
        if rows:
            conn.executemany("INSERT INTO issue_timeline VALUES (?,?,?,?,?)", rows)

        conn.execute(sql_issue_fts, (
            uid,
            issue_id,
            as_text(first(prof, "title")) or as_text(first(summ, "title")),
            as_text(first(prof, "revision_description")),
            as_text(first(prof, "reason_for_revision")),
            as_text(first(prof, "business_case")),
            exec_summary,
            as_text(first(summ, "background")),
            as_text(first(summ, "key_change")),
            " ".join(t for t in (as_text(first(summ, "impacts_summary")),
                                 as_text(summ.get("impact_analysis"))) if t),
            cur_status,
            as_text(first(summ, "stakeholder_key_debates")),
            as_text(first(summ, "ercot_opinion")),
            as_text(first(summ, "imm_opinion")),
            " ".join(sorted(sections))))

        # Document level - the per-file summaries the profiler already wrote.
        for entry in source_docs:
            if not isinstance(entry, dict):
                continue
            doc_uid += 1
            conn.execute(sql_doc, (
                doc_uid, uid, issue_id,
                scalar(entry.get("file")), scalar(entry.get("title")),
                scalar(entry.get("doc_type")), norm_date(entry.get("date")),
                norm_date(entry.get("date_posted")), scalar(entry.get("author")),
                scalar(entry.get("submitter")),
                scalar(entry.get("download_url"))))
            conn.execute(sql_doc_fts, (
                doc_uid, issue_id,
                as_text(entry.get("file")), as_text(entry.get("doc_type")),
                as_text(entry.get("title")), as_text(entry.get("summary")),
                as_text(entry.get("description")),
                as_text(first(entry, "justification", "revision_reason")),
                as_text(entry.get("detailed_background")),
                as_text(entry.get("key_points"))))

    log("  market rules : %d issues (%d with AI summaries), %d documents"
        % (uid, n_summaries, doc_uid))
    return uid, doc_uid


# --- Stakeholder meetings ---------------------------------------------------
def iter_meeting_profiles():
    if not os.path.isdir(STK_ROOT):
        return
    for committee in sorted(os.listdir(STK_ROOT)):
        cmte_dir = os.path.join(STK_ROOT, committee)
        if not os.path.isdir(cmte_dir):
            continue
        for meeting in sorted(os.listdir(cmte_dir)):
            quick = os.path.join(cmte_dir, meeting, "Quick runs")
            if not os.path.isdir(quick):
                continue
            for name in sorted(os.listdir(quick)):
                if name.lower().endswith("profile.json"):
                    yield committee, meeting, os.path.join(quick, name)


def index_meetings(conn):
    sql_meet = """INSERT INTO meetings (uid, committee, committee_full_name,
            meeting_date, meeting_type, calendar_url, chair, vice_chair,
            next_meeting_date, doc_count, profile_path)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)"""
    sql_meet_fts = fts_insert("meetings_fts", MEETINGS_FTS_COLS)

    uid = n_docs = 0
    for committee, meeting, path in iter_meeting_profiles():
        prof = read_json(path)
        if not isinstance(prof, dict):
            continue
        uid += 1

        group = prof.get("group_summary")
        group = group if isinstance(group, dict) else {}
        meet = prof.get("meeting_summary")
        meet = meet if isinstance(meet, dict) else {}
        doc_list = sorted(set(flatten_strings(prof.get("documents"))))
        meeting_date = (norm_date(prof.get("meeting_date"))
                        or norm_date(meeting) or meeting)

        conn.execute(sql_meet, (
            uid,
            scalar(prof.get("committee")) or committee,
            scalar(prof.get("committee_full_name")),
            meeting_date,
            scalar(prof.get("meeting_type")),
            scalar(prof.get("calendar_url")),
            scalar(prof.get("chair")) or scalar(group.get("leadership")),
            scalar(prof.get("vice_chair")),
            scalar(prof.get("next_meeting_date")),
            len(doc_list),
            os.path.relpath(path, PROJECT_ROOT)))

        if doc_list:
            n_docs += len(doc_list)
            conn.executemany(
                "INSERT INTO meeting_documents VALUES (?,?,?,?)",
                [(uid, committee, meeting_date, f) for f in doc_list])

        conn.execute(sql_meet_fts, (
            uid,
            as_text(prof.get("committee")) or committee,
            as_text(prof.get("committee_full_name")),
            meeting_date,
            as_text(first(group, "overview")),
            " ".join(t for t in (as_text(first(group, "voting_structure")),
                                 as_text(group.get("voting_parties"))) if t),
            as_text(meet.get("topics")),
            as_text(meet.get("debates")),
            as_text(meet.get("voting_outcomes")),
            as_text(prof.get("key_discussion_topics")),
            as_text(prof.get("action_items")),
            as_text(prof.get("agenda_items")),
            as_text(prof.get("working_group_reports")),
            as_text(prof.get("ballot_results")),
            " ".join(doc_list)))

    log("  meetings     : %d meetings, %d documents" % (uid, n_docs))
    return uid


# --- Reference vocabulary ---------------------------------------------------
def index_terms(conn):
    """Load the glossary + market keywords - the source of query expansion."""
    rows = []

    gloss = read_json(os.path.join(REF_INFO, "ercot_glossary.json")) or {}
    for entry in gloss.get("terms", []):
        if not isinstance(entry, dict):
            continue
        term = scalar(first(entry, "term_s", "term"))
        if not term:
            continue
        definition = as_text(first(entry, "definition", "definition_html_raw"))
        definition = re.sub(r"<[^>]+>", " ", definition)
        definition = re.sub(r"\s+", " ", definition).strip()
        # A glossary entry whose definition is just a short phrase is an acronym
        # expansion ("ACE" -> "Area Control Error"); that pairing is exactly
        # what query expansion needs, so record it as term + acronym.
        is_acronym = bool(re.fullmatch(r"[A-Z][A-Za-z0-9/\-]{1,9}", term)) \
            and term.upper() == term
        if is_acronym and 0 < len(definition) <= 60:
            rows.append((definition, term, None, definition, "glossary", 0))
        else:
            rows.append((term, term if is_acronym else None, None,
                         definition, "glossary", 0))

    kw = read_json(os.path.join(REF_INFO, "ercot_market_keywords.json")) or {}
    for entry in kw.get("keywords", []):
        if not isinstance(entry, dict):
            continue
        term = scalar(entry.get("term"))
        if not term:
            continue
        acronym = scalar(entry.get("acronym"))
        # "Locational Marginal Price (LMP)" carries its own acronym inline.
        if not acronym:
            m = re.search(r"\(([A-Z][A-Za-z0-9/\-]{1,9})\)\s*$", term)
            if m:
                acronym = m.group(1)
        bare = re.sub(r"\s*\([^)]*\)\s*$", "", term).strip() or term
        rows.append((bare, acronym, scalar(entry.get("category")),
                     as_text(entry.get("description")), "keywords",
                     1 if entry.get("trending") else 0))

    conn.executemany("INSERT INTO terms VALUES (?,?,?,?,?,?)", rows)
    log("  vocabulary   : %d terms (glossary + market keywords, for expansion)"
        % len(rows))
    return len(rows)


# --- Build ------------------------------------------------------------------
def build(out_path):
    tmp_path = out_path + ".tmp"
    for stale in (tmp_path, tmp_path + "-journal"):
        if os.path.exists(stale):
            os.remove(stale)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.executescript(SCHEMA)
        with conn:
            log("Indexing the derived knowledge layer:")
            n_issues, n_docs = index_market_rules(conn)
            n_meetings = index_meetings(conn)
            n_terms = index_terms(conn)
            # `source_documents` is not written by the profilers - they rewrite
            # Profile.json without it, and gen_mkt_doc_summaries.py (routine
            # step 25) adds it back. A build in the window between those two
            # steps therefore indexes every issue but no documents at all, and
            # silently returns nothing for document-level search. Say so loudly
            # rather than leaving a half-useful index that looks fine.
            warning = None
            if n_issues and not n_docs:
                warning = ("source_documents absent from all %d profiles - "
                           "document-level search is EMPTY. Run "
                           "gen_mkt_doc_summaries.py (run_routine.py step 25) "
                           "and rebuild." % n_issues)
            elif n_issues and n_docs < n_issues:
                warning = ("only %d documents across %d issues - profiles may "
                           "be mid-rewrite; rebuild once the routine finishes."
                           % (n_docs, n_issues))

            conn.executemany("INSERT INTO meta VALUES (?,?)", [
                ("built_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
                ("issues", str(n_issues)),
                ("documents", str(n_docs)),
                ("meetings", str(n_meetings)),
                ("terms", str(n_terms)),
                ("project_root", PROJECT_ROOT)]
                + ([("warning", warning)] if warning else []))
            if warning:
                print("WARNING: " + warning, file=sys.stderr, flush=True)
        with conn:
            for table in ("issues_fts", "docs_fts", "meetings_fts"):
                conn.execute("INSERT INTO %s(%s) VALUES('optimize')"
                             % (table, table))
        conn.execute("VACUUM")
    finally:
        conn.close()

    try:
        os.replace(tmp_path, out_path)
    except OSError as e:
        # Windows refuses the replace while another process holds the live file.
        log("! could not replace %s (%s); the new index is at %s"
            % (out_path, e, tmp_path))
        return tmp_path
    return out_path


def main():
    global QUIET
    parser = argparse.ArgumentParser(
        description="Build the Power.Talks study index (SQLite + FTS5)")
    parser.add_argument("--out", default=DEFAULT_DB,
                        help="output database path (default: study_index.db)")
    parser.add_argument("--quiet", action="store_true",
                        help="only print the one-line result")
    args = parser.parse_args()
    QUIET = args.quiet

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    t0 = time.time()
    path = build(args.out)
    size_mb = os.path.getsize(path) / 1024.0 / 1024.0
    print("study index built: %s (%.1f MB) in %.1fs"
          % (os.path.relpath(path, PROJECT_ROOT), size_mb, time.time() - t0),
          flush=True)


if __name__ == "__main__":
    main()
