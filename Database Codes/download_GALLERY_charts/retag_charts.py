#!/usr/bin/env python3
"""retag_charts.py — rebuild chart keyword links from the current vocabulary.

    py -3 retag_charts.py --dry-run      # report what would change, touch nothing
    py -3 retag_charts.py                # apply, with a per-concept diff
    py -3 retag_charts.py --quiet        # one line (nightly / headless)

This is what makes the vocabulary editable. Every chart's matchable text is
either already in its columns (title, worksheet name, document name) or stored
in `gallery_charts.scan_text` (axis titles, series names), so a keyword can be
added, split, renamed or rejected and the whole corpus re-tagged in seconds --
without reopening a single workbook through Excel COM.

Only `source='scan'` links are rebuilt. Links the AI assigned while reading a
PDF page (`source='ai'`) and anything set by hand (`source='manual'`) are left
alone: a literal scan over a title cannot reproduce what a model concluded from
a full page, so it must not delete it.
"""
import argparse
import collections
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gallery_db as db  # noqa: E402


def has_column(conn, table, column):
    with conn.cursor() as cur:
        cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s AND column_name = %s""",
                    (db.SCHEMA, table, column))
        return cur.fetchone()[0] > 0


def fetch_charts(conn):
    """A dry run must not migrate anything, so read whichever columns exist."""
    cols = ["chart_id", "chart_title", "doc_name", "doc_type", "page_num"]
    if has_column(conn, db.CHARTS_TABLE, "scan_text"):
        cols.append("scan_text")
    with conn.cursor() as cur:
        cur.execute(f"SELECT {', '.join(cols)} FROM `{db.CHARTS_TABLE}`")
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_links(conn):
    """chart_id -> {source: {keyword_id: keyword}}"""
    has_source = has_column(conn, db.LINKS_TABLE, "source")
    sel = "chart_id, keyword_id, keyword" + (", source" if has_source else "")
    out = collections.defaultdict(lambda: collections.defaultdict(dict))
    with conn.cursor() as cur:
        cur.execute(f"SELECT {sel} FROM `{db.LINKS_TABLE}`")
        for row in cur.fetchall():
            cid, kid, kw = row[0], row[1], row[2]
            src = (row[3] if has_source else None) or "scan"
            out[cid][src][kid] = kw
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ap.add_argument("--quiet", action="store_true", help="one summary line")
    ap.add_argument("--top", type=int, default=25, help="how many concepts to list (default 25)")
    args = ap.parse_args()

    vocab = db.load_concepts()
    conn = db.connect()
    try:
        db.ensure_tables(conn)
        if not args.dry_run:
            db.ensure_columns(conn, log=(None if args.quiet else print))

        charts = fetch_charts(conn)
        links = fetch_links(conn)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        added = collections.Counter()
        removed = collections.Counter()
        kept = collections.Counter()
        tagged_before = sum(1 for c in charts if links.get(c["chart_id"]))
        tagged_after = 0
        ins, dele, upd = [], [], []

        for row in charts:
            cid = row["chart_id"]
            fields = db.chart_fields(row, row.get("scan_text"))
            matched = vocab.match(fields)                       # [(kid, term, where)]
            want = {kid: (term, where) for kid, term, where in matched}

            by_src = links.get(cid, {})
            have_scan = dict(by_src.get("scan", {}))
            protected = {}
            for src, kws in by_src.items():
                if src != "scan":
                    protected.update(kws)

            for kid, (term, where) in want.items():
                if kid in protected:
                    continue       # an ai/manual link already owns this concept
                if kid in have_scan:
                    kept[term] += 1
                else:
                    added[term] += 1
                # written either way, so `matched_in` always reflects the
                # evidence behind the link as it stands now
                ins.append((kid, term, cid, now, "scan", where))
            for kid, term in have_scan.items():
                if kid not in want:
                    removed[term] += 1
                    dele.append((cid, kid))

            final = dict(protected)
            final.update({kid: term for kid, (term, _) in want.items()})
            if final:
                tagged_after += 1
            upd.append((json.dumps(sorted(final.values()), ensure_ascii=False), cid))

        if not args.dry_run:
            with conn.cursor() as cur:
                for cid, kid in dele:
                    cur.execute(f"DELETE FROM `{db.LINKS_TABLE}` "
                                f"WHERE chart_id = %s AND keyword_id = %s AND source = 'scan'",
                                (cid, kid))
                for kid, term, cid, stamp, src, where in ins:
                    cur.execute(
                        f"""INSERT INTO `{db.LINKS_TABLE}`
                              (keyword_id, keyword, chart_id, record_timestamp, source, matched_in)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE keyword = VALUES(keyword),
                              source = VALUES(source), matched_in = VALUES(matched_in)""",
                        (kid, term, cid, stamp, src, where))
                for payload, cid in upd:
                    cur.execute(f"UPDATE `{db.CHARTS_TABLE}` SET keywords = %s WHERE chart_id = %s",
                                (payload, cid))
            conn.commit()

        total_links = sum(kept.values()) + sum(added.values())
        if args.quiet:
            print(f"Retag: {len(charts)} charts | {total_links} scan links "
                  f"(+{sum(added.values())} -{sum(removed.values())}) | "
                  f"coverage {tagged_before}->{tagged_after}"
                  + ("  [dry run]" if args.dry_run else ""))
            return 0

        print(f"{'' if not args.dry_run else '[dry run] '}"
              f"{len(charts)} charts, vocabulary of {len(vocab)} concepts\n")
        print(f"  scan links : {sum(kept.values())} kept, "
              f"{sum(added.values())} added, {sum(removed.values())} removed "
              f"-> {total_links}")
        print(f"  charts with at least one keyword: {tagged_before} -> {tagged_after} "
              f"({tagged_after / max(len(charts), 1):.0%})")
        concepts_used = len(set(list(kept) + list(added)))
        print(f"  concepts in use: {concepts_used} of {len(vocab)}\n")

        if added:
            print("  gained")
            for term, n in added.most_common(args.top):
                print(f"    +{n:<6} {term}")
        if removed:
            print("\n  lost")
            for term, n in removed.most_common(args.top):
                print(f"    -{n:<6} {term}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
