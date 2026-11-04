#!/usr/bin/env python3
"""search.py — Query the Power.Talks study index.

Two kinds of question, deliberately kept apart:

  Tier 1  exact and *complete* — "every NPRR touching Protocol section 25.1",
          "the full record for NPRR1176". Plain SQL over the structured tables,
          so the answer is the whole set, not a ranked sample.
  Tier 2  discovery — "what has ERCOT discussed about co-located load?" BM25
          full-text over the AI summaries, profiles and per-document write-ups,
          with the ERCOT glossary and market-keyword list used to expand
          acronyms and synonyms before the query runs.

Discovery is a *starting point*: it returns issue ids, meeting dates and the
on-disk paths of the real source documents. Read those documents before drawing
a conclusion - the index holds the derived summaries, not the authoritative text.

Usage:
    # discovery
    py -3 search.py "co-located load"
    py -3 search.py "ancillary services" --category NPRR --from 2023-01-01
    py -3 search.py "state of charge" --what issues --limit 20
    py -3 search.py "ECRS" --json

    # completeness / exact lookup
    py -3 search.py --section 25.1
    py -3 search.py --issue NPRR1176
    py -3 search.py "real-time co-optimization" --count
    py -3 search.py --terms LFL
    py -3 search.py --stats
"""

import argparse
import json
import os
import re
import sqlite3
import sys

HERE         = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_DB   = os.path.join(HERE, "study_index.db")

# BM25 column weights, in each table's declared column order. Hand-written
# prose (titles, executive summaries, debates) outranks boilerplate.
W_ISSUES = (2.0, 8.0, 5.0, 3.0, 2.0, 6.0, 3.0, 4.0, 2.0, 2.0, 2.0, 1.5, 1.5, 1.0)
W_DOCS = (1.0, 1.0, 1.0, 4.0, 5.0, 5.0, 3.0, 3.0, 4.0)
W_MEETINGS = (2.0, 2.0, 1.0, 3.0, 1.0, 6.0, 6.0, 4.0, 6.0, 3.0, 4.0, 3.0, 2.0, 1.5)

# Vocabulary the ERCOT glossary and keyword list do not pair up, but that the
# corpus uses interchangeably. Kept small and explicit on purpose.
EXTRA_SYNONYMS = {
    "co-located load": ["colocated load", "co-location", "behind the meter load"],
    "large flexible load": ["LFL", "large load", "controllable load resource"],
    "crypto load": ["cryptocurrency mining", "data center load", "bitcoin mining"],
    "data center": ["data centre", "hyperscale load", "large load"],
    "battery": ["energy storage resource", "ESR", "BESS", "storage"],
    "real-time co-optimization": ["RTC", "RTC+B", "co-optimization"],
    "state of charge": ["SOC", "state-of-charge"],
    "firming": ["firm fuel", "dispatchable reliability reserve"],
    "winterization": ["weatherization", "weather emergency preparedness"],
    "interconnection": ["interconnection queue", "generation interconnection"],
    "inverter-based resource": ["IBR", "inverter based resources"],
    "demand response": ["DR", "load resource", "emergency response service", "ERS"],
}


# --- Connection -------------------------------------------------------------
def connect(db_path):
    if not os.path.isfile(db_path):
        sys.exit("No index at %s\nBuild it first:  py -3 \"%s\""
                 % (db_path, os.path.join(HERE, "build_index.py")))
    conn = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"),
                           uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# --- Query expansion --------------------------------------------------------
def expand(conn, topic):
    """Return the topic plus every acronym/expansion the vocabulary pairs with it.

    This is what buys most of the semantic reach a vector index would give:
    'LFL' finds 'Large Flexible Load' and the reverse, because the glossary
    already records the pairing.
    """
    phrases = [topic.strip()]
    low = topic.lower().strip()

    for key, extras in EXTRA_SYNONYMS.items():
        pool = [key] + extras
        if any(p.lower() in low or low in p.lower() for p in pool):
            phrases.extend(pool)

    rows = conn.execute(
        "SELECT term, acronym FROM terms "
        "WHERE acronym IS NOT NULL AND acronym <> ''").fetchall()
    for row in rows:
        term, acronym = (row["term"] or "").strip(), (row["acronym"] or "").strip()
        if not term or not acronym:
            continue
        # match the acronym as a whole word, or the spelled-out term anywhere
        if re.search(r"\b%s\b" % re.escape(acronym), topic, re.IGNORECASE):
            phrases += [term, acronym]
        elif term.lower() in low:
            phrases += [term, acronym]

    seen, out = set(), []
    for phrase in phrases:
        key = phrase.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(phrase.strip())
    return out


def fts_phrase(text):
    """Quote a phrase for FTS5 MATCH, dropping syntax characters."""
    cleaned = re.sub(r"[^\w\s\-/.]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return '"%s"' % cleaned.replace('"', '""') if cleaned else ""


def build_match(phrases, strategy):
    """Compose an FTS5 MATCH expression.

    phrase : the phrases as phrases, OR'd  - most precise
    all    : every significant word must appear (AND)
    any    : any significant word (OR)      - last resort
    """
    if strategy == "phrase":
        parts = [p for p in (fts_phrase(x) for x in phrases) if p]
        return " OR ".join(parts)

    words, seen = [], set()
    stop = {"the", "a", "an", "of", "and", "or", "for", "to", "in", "on", "at",
            "by", "with", "is", "are", "was", "were", "be", "as", "that", "it"}
    for phrase in phrases:
        for word in re.findall(r"[\w/]+", phrase):
            low = word.lower()
            if len(low) > 1 and low not in stop and low not in seen:
                seen.add(low)
                words.append('"%s"' % word)
    if not words:
        return ""
    return (" AND " if strategy == "all" else " OR ").join(words)


# --- Tier 2: discovery ------------------------------------------------------
def search_issues(conn, match, args):
    where, params = ["i.issue_id IS NOT NULL"], [match]
    if args.category:
        where.append("UPPER(i.category) = ?")
        params.append(args.category.upper())
    if args.status:
        where.append("i.status LIKE ?")
        params.append("%" + args.status + "%")
    if getattr(args, "date_from", None):
        where.append("i.date_posted >= ?")
        params.append(args.date_from)
    if getattr(args, "date_to", None):
        where.append("i.date_posted <= ?")
        params.append(args.date_to)

    sql = """
        SELECT i.issue_id, i.category, i.title, i.status, i.date_posted,
               i.sponsor_company, i.sponsor_name, i.doc_count, i.profile_path,
               i.executive_summary,
               snippet(issues_fts, -1, '[', ']', ' ... ', 14) AS snip,
               -bm25(issues_fts, %s) AS score
        FROM issues_fts
        JOIN issues i ON i.uid = issues_fts.rowid
        WHERE issues_fts MATCH ? AND %s
        ORDER BY score DESC LIMIT ?
    """ % (", ".join(str(w) for w in W_ISSUES), " AND ".join(where[1:]) or "1=1")
    params.append(args.limit)
    return [dict(r) for r in conn.execute(sql, params)]


def search_docs(conn, match, args):
    where, params = [], [match]
    if args.category:
        where.append("UPPER(i.category) = ?")
        params.append(args.category.upper())
    if getattr(args, "date_from", None):
        where.append("COALESCE(d.date, i.date_posted) >= ?")
        params.append(args.date_from)
    if getattr(args, "date_to", None):
        where.append("COALESCE(d.date, i.date_posted) <= ?")
        params.append(args.date_to)

    sql = """
        SELECT d.issue_id, d.file, d.doc_type, d.date, d.download_url,
               i.category, i.title AS issue_title,
               snippet(docs_fts, -1, '[', ']', ' ... ', 14) AS snip,
               -bm25(docs_fts, %s) AS score
        FROM docs_fts
        JOIN documents d ON d.uid = docs_fts.rowid
        JOIN issues i ON i.uid = d.issue_uid
        WHERE docs_fts MATCH ? AND %s
        ORDER BY score DESC LIMIT ?
    """ % (", ".join(str(w) for w in W_DOCS), " AND ".join(where) or "1=1")
    params.append(args.limit)
    return [dict(r) for r in conn.execute(sql, params)]


def search_meetings(conn, match, args):
    where, params = [], [match]
    if args.committee:
        where.append("UPPER(m.committee) = ?")
        params.append(args.committee.upper())
    if getattr(args, "date_from", None):
        where.append("m.meeting_date >= ?")
        params.append(args.date_from)
    if getattr(args, "date_to", None):
        where.append("m.meeting_date <= ?")
        params.append(args.date_to)

    sql = """
        SELECT m.committee, m.committee_full_name, m.meeting_date,
               m.meeting_type, m.doc_count, m.profile_path, m.calendar_url,
               snippet(meetings_fts, -1, '[', ']', ' ... ', 14) AS snip,
               -bm25(meetings_fts, %s) AS score
        FROM meetings_fts
        JOIN meetings m ON m.uid = meetings_fts.rowid
        WHERE meetings_fts MATCH ? AND %s
        ORDER BY score DESC LIMIT ?
    """ % (", ".join(str(w) for w in W_MEETINGS), " AND ".join(where) or "1=1")
    params.append(args.limit)
    return [dict(r) for r in conn.execute(sql, params)]


def count_matches(conn, match, args):
    out = {}
    for name, table, join in (
            ("issues", "issues_fts", "JOIN issues i ON i.uid = issues_fts.rowid"),
            ("documents", "docs_fts", "JOIN documents d ON d.uid = docs_fts.rowid"),
            ("meetings", "meetings_fts",
             "JOIN meetings m ON m.uid = meetings_fts.rowid")):
        row = conn.execute("SELECT COUNT(*) AS n FROM %s %s WHERE %s MATCH ?"
                           % (table, join, table), (match,)).fetchone()
        out[name] = row["n"]
    return out


def empty_result(topic, phrases, note):
    return {"topic": topic, "expanded_to": phrases, "match_strategy": "none",
            "fts_query": "", "note": note,
            "counts": {"issues": 0, "documents": 0, "meetings": 0},
            "issues": [], "documents": [], "meetings": []}


def discover(conn, topic, args):
    """Run the tiered search, loosening the query only if nothing matched."""
    phrases = [topic] if args.no_expand else expand(conn, topic)
    wanted = {"issues", "documents", "meetings"} if args.what == "all" \
        else {args.what}

    result = empty_result(topic, phrases,
                          "no searchable terms in the topic")
    for strategy in ("phrase", "all", "any"):
        match = build_match(phrases, strategy)
        if not match:
            continue
        result = {
            "topic": topic,
            "expanded_to": phrases,
            "match_strategy": strategy,
            "fts_query": match,
            "counts": count_matches(conn, match, args),
            "issues": search_issues(conn, match, args) if "issues" in wanted else [],
            "documents": search_docs(conn, match, args) if "documents" in wanted else [],
            "meetings": search_meetings(conn, match, args) if "meetings" in wanted else [],
        }
        if result["issues"] or result["documents"] or result["meetings"]:
            return result
        if args.strategy != "auto":
            return result
    return result


# --- Tier 1: exact and complete ---------------------------------------------
def by_section(conn, section, exact=False):
    """Every issue touching a section - the complete set, not a ranked sample.

    A bare number matches the whole subtree ("6.5" also returns 6.5.7.3) unless
    --exact-section is given. A non-numeric argument falls back to matching the
    recorded section text, so titles ("Definitions") work too.
    """
    section = section.strip()
    if re.fullmatch(r"\d{1,2}(?:\.\d{1,3})*", section):
        if exact:
            where, params = "s.section_num = ?", (section,)
        else:
            where = "(s.section_num = ? OR s.section_num LIKE ?)"
            params = (section, section + ".%")
    else:
        where, params = "s.section LIKE ?", ("%" + section + "%",)

    rows = conn.execute(
        """SELECT i.issue_id, i.category, i.title, i.status, i.date_posted,
                  i.profile_path,
                  GROUP_CONCAT(DISTINCT COALESCE(s.section_num, s.section))
                      AS matched_sections
           FROM issue_sections s JOIN issues i ON i.uid = s.issue_uid
           WHERE """ + where + """
           GROUP BY i.uid
           ORDER BY i.category, i.issue_number""", params).fetchall()
    return [dict(r) for r in rows]


def issue_record(conn, issue_id):
    row = conn.execute("SELECT * FROM issues WHERE UPPER(issue_id) = ?",
                       (issue_id.upper(),)).fetchone()
    if not row:
        return None
    rec = dict(row)
    uid = rec["uid"]
    rec["sections"] = [r["section"] for r in conn.execute(
        "SELECT section FROM issue_sections WHERE issue_uid = ? ORDER BY section",
        (uid,))]
    rec["related_documents"] = [r["document"] for r in conn.execute(
        "SELECT document FROM issue_related_docs WHERE issue_uid = ?", (uid,))]
    rec["timeline"] = [dict(r) for r in conn.execute(
        "SELECT date, event, doc FROM issue_timeline WHERE issue_uid = ? "
        "ORDER BY date", (uid,))]
    rec["documents"] = [dict(r) for r in conn.execute(
        "SELECT file, title, doc_type, date, download_url FROM documents "
        "WHERE issue_uid = ? ORDER BY date, file", (uid,))]
    rec["folder"] = os.path.dirname(os.path.dirname(rec["profile_path"] or ""))
    return rec


def lookup_terms(conn, text):
    rows = conn.execute(
        """SELECT term, acronym, category, description, source, trending
           FROM terms
           WHERE term LIKE ? OR acronym LIKE ? OR description LIKE ?
           ORDER BY source, term LIMIT 40""",
        ("%" + text + "%",) * 3).fetchall()
    return [dict(r) for r in rows]


def index_stats(conn):
    stats = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM meta")}
    stats["committees"] = conn.execute(
        "SELECT COUNT(DISTINCT committee) AS n FROM meetings").fetchone()["n"]
    stats["categories"] = [r["category"] for r in conn.execute(
        "SELECT DISTINCT category FROM issues ORDER BY category")]
    stats["meeting_date_range"] = list(conn.execute(
        "SELECT MIN(meeting_date), MAX(meeting_date) FROM meetings").fetchone())
    stats["issue_date_range"] = list(conn.execute(
        "SELECT MIN(date_posted), MAX(date_posted) FROM issues "
        "WHERE date_posted IS NOT NULL").fetchone())
    return stats


# --- Rendering --------------------------------------------------------------
def clean(text, width=240):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[:width] + ("..." if len(text) > width else "")


def render_discovery(res):
    out = []
    out.append("TOPIC: %s" % res["topic"])
    if res["expanded_to"][1:]:
        out.append("expanded: %s" % ", ".join(res["expanded_to"][:12]))
    counts = res["counts"]
    out.append("matches: %d issues, %d documents, %d meetings  (strategy: %s)"
               % (counts["issues"], counts["documents"], counts["meetings"],
                  res["match_strategy"]))

    if res["issues"]:
        out.append("\n--- ISSUES " + "-" * 56)
        for r in res["issues"]:
            out.append("%-12s %-7s %s" % (r["issue_id"], r["date_posted"] or "-",
                                          clean(r["title"], 90)))
            out.append("    status: %s | sponsor: %s | %d docs"
                       % (clean(r["status"], 40) or "-",
                          clean(r["sponsor_company"] or r["sponsor_name"], 40) or "-",
                          r["doc_count"] or 0))
            out.append("    match: %s" % clean(r["snip"], 200))
            out.append("    folder: %s" % os.path.dirname(
                os.path.dirname(r["profile_path"] or "")))

    if res["documents"]:
        out.append("\n--- DOCUMENTS " + "-" * 53)
        for r in res["documents"]:
            out.append("%-12s %-10s %s" % (r["issue_id"], r["date"] or "-",
                                           clean(r["doc_type"], 34) or "-"))
            out.append("    file:  %s" % clean(r["file"], 110))
            out.append("    match: %s" % clean(r["snip"], 200))

    if res["meetings"]:
        out.append("\n--- MEETINGS " + "-" * 54)
        for r in res["meetings"]:
            out.append("%-10s %-11s %s" % (r["committee"], r["meeting_date"] or "-",
                                           clean(r["committee_full_name"], 60) or ""))
            out.append("    match: %s" % clean(r["snip"], 200))
            out.append("    profile: %s" % (r["profile_path"] or "-"))

    if not (res["issues"] or res["documents"] or res["meetings"]):
        if res.get("note"):
            out.append("\n%s" % res["note"])
        out.append("\nNo matches. Try --terms to check the vocabulary, a broader "
                   "phrase, or --strategy any.")
    return "\n".join(out)


def render_section(section, rows):
    out = ["SECTION %s - %d issue(s) [complete set from Tier 1]"
           % (section, len(rows))]
    for r in rows:
        out.append("%-12s %-11s %-22s %s"
                   % (r["issue_id"], r["date_posted"] or "-",
                      clean(r["matched_sections"], 22),
                      clean(r["title"], 64)))
    return "\n".join(out)


def render_issue(rec):
    out = ["%s - %s" % (rec["issue_id"], clean(rec["title"], 100)),
           "category: %s | status: %s | posted: %s | effective: %s"
           % (rec["category"], rec["status"] or "-", rec["date_posted"] or "-",
              rec["effective_date"] or "-"),
           "sponsor: %s (%s)" % (clean(rec["sponsor_name"], 70) or "-",
                                 rec["sponsor_company"] or "-"),
           "folder: %s" % rec["folder"]]
    if rec["sections"]:
        out.append("sections: %s" % ", ".join(rec["sections"][:20]))
    if rec["executive_summary"]:
        out.append("\nexecutive summary:\n  %s" % clean(rec["executive_summary"], 1200))
    if rec["current_status"]:
        out.append("\ncurrent status:\n  %s" % clean(rec["current_status"], 600))
    if rec["timeline"]:
        out.append("\ntimeline:")
        for t in rec["timeline"]:
            out.append("  %-11s %-34s %s" % (t["date"] or "-",
                                             clean(t["event"], 34) or "-",
                                             clean(t["doc"], 50) or ""))
    if rec["documents"]:
        out.append("\nsource documents (%d):" % len(rec["documents"]))
        for d in rec["documents"]:
            out.append("  %-11s %-30s %s" % (d["date"] or "-",
                                             clean(d["doc_type"], 30) or "-",
                                             clean(d["file"], 70)))
    return "\n".join(out)


def render_terms(rows):
    out = ["%d vocabulary match(es)" % len(rows)]
    for r in rows:
        out.append("%-46s %-10s %-9s %s"
                   % (clean(r["term"], 46), r["acronym"] or "-", r["source"],
                      clean(r["description"], 80)))
    return "\n".join(out)


# --- CLI --------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Query the Power.Talks study index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[-1])
    p.add_argument("topic", nargs="?", help="topic to search for (Tier 2)")
    p.add_argument("--db", default=DEFAULT_DB, help="index path")
    p.add_argument("--what", choices=["all", "issues", "documents", "meetings"],
                   default="all", help="which tables to search")
    p.add_argument("--limit", type=int, default=12,
                   help="max rows per section (default 12)")
    p.add_argument("--category", help="restrict to NPRR / NOGRR / PGRR / ...")
    p.add_argument("--status", help="substring match on issue status")
    p.add_argument("--committee", help="restrict meetings to one committee")
    p.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD",
                   help="earliest date")
    p.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD",
                   help="latest date")
    p.add_argument("--no-expand", action="store_true",
                   help="do not expand acronyms/synonyms")
    p.add_argument("--strategy", choices=["auto", "phrase", "all", "any"],
                   default="auto", help="match strategy (default: auto)")
    p.add_argument("--count", action="store_true",
                   help="only report how many records match")
    p.add_argument("--section", help="Tier 1: every issue touching a section "
                                     "(a bare number includes its subsections)")
    p.add_argument("--exact-section", action="store_true",
                   help="with --section, do not include subsections")
    p.add_argument("--issue", help="Tier 1: the full record for one issue id")
    p.add_argument("--terms", help="look up the glossary / keyword vocabulary")
    p.add_argument("--stats", action="store_true", help="index coverage")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    conn = connect(args.db)

    if args.stats:
        stats = index_stats(conn)
        print(json.dumps(stats, indent=2) if args.json else
              "\n".join("%-20s %s" % (k, v) for k, v in stats.items()))
        return

    if args.terms:
        rows = lookup_terms(conn, args.terms)
        print(json.dumps(rows, indent=2) if args.json else render_terms(rows))
        return

    if args.section:
        rows = by_section(conn, args.section, args.exact_section)
        print(json.dumps(rows, indent=2) if args.json else
              render_section(args.section, rows))
        return

    if args.issue:
        rec = issue_record(conn, args.issue)
        if not rec:
            sys.exit("No such issue: %s" % args.issue)
        print(json.dumps(rec, indent=2) if args.json else render_issue(rec))
        return

    if not args.topic:
        p.print_help()
        return

    if args.strategy != "auto":
        phrases = [args.topic] if args.no_expand else expand(conn, args.topic)
        match = build_match(phrases, args.strategy)
        if not match:
            res = empty_result(args.topic, phrases,
                               "no searchable terms in the topic")
        else:
            res = {"topic": args.topic, "expanded_to": phrases,
                   "match_strategy": args.strategy, "fts_query": match,
                   "counts": count_matches(conn, match, args),
                   "issues": search_issues(conn, match, args),
                   "documents": search_docs(conn, match, args),
                   "meetings": search_meetings(conn, match, args)}
    else:
        res = discover(conn, args.topic, args)

    if args.count:
        print(json.dumps(res["counts"], indent=2) if args.json else
              "issues %d | documents %d | meetings %d  (strategy %s)"
              % (res["counts"]["issues"], res["counts"]["documents"],
                 res["counts"]["meetings"], res["match_strategy"]))
        return

    print(json.dumps(res, indent=2) if args.json else render_discovery(res))


if __name__ == "__main__":
    main()
