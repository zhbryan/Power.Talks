#!/usr/bin/env python3
"""import_ai_keywords.py — restore model-assigned keywords from the extraction state.

    py -3 import_ai_keywords.py --dry-run
    py -3 import_ai_keywords.py

A PDF chart's keywords come from the model reading the whole page, which a
literal scan over a title cannot reproduce. Those links are therefore marked
`source='ai'` in `gallery_keywords` so `retag_charts.py` leaves them alone.

`Documents Database/GALLERY/_extraction_state.json` already records, per source
document, the keywords the model chose for each chart -- so they can be
replayed without spending a single AI call. Each term is resolved against the
current vocabulary: unchanged terms map to themselves, renamed and split ones
follow `replaces:`, and a term the vocabulary has since rejected is dropped and
reported (that is the vocabulary doing its job).
"""
import argparse
import collections
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "reference_info"))
import gallery_db as db        # noqa: E402
import vocabulary as V         # noqa: E402

STATE = os.path.join(db.PROJECT_ROOT, "Documents Database", "GALLERY",
                     "_extraction_state.json")


def resolve(term, vocab, replaced):
    """Old keyword string -> current Concept(s), or [] if it was rejected."""
    n = V.norm(term)
    hit = vocab.by_term.get(n)
    if hit and hit.status != "retired":
        return [hit]
    return [c for c in replaced.get(n, []) if c.status != "retired"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(STATE):
        print(f"no extraction state at {STATE}")
        return 1
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)

    vocab = V.load()
    replaced = vocab.replaced_terms()

    wanted = collections.defaultdict(dict)      # chart_id -> {kid: term}
    dropped = collections.Counter()
    for path, entry in (state.get("files") or {}).items():
        if (entry.get("doc_type") or "").lower() != "pdf":
            continue                            # only the AI path produces these
        for chart in entry.get("charts") or []:
            cid = chart.get("chart_id")
            for term in chart.get("keywords") or []:
                hits = resolve(term, vocab, replaced)
                if not hits:
                    dropped[term] += 1
                    continue
                for c in hits:
                    wanted[cid][c.keyword_id] = c.term

    conn = db.connect()
    try:
        db.ensure_tables(conn)
        if not args.dry_run:
            db.ensure_columns(conn)
        with conn.cursor() as cur:
            cur.execute(f"SELECT chart_id FROM `{db.CHARTS_TABLE}`")
            known = {r[0] for r in cur.fetchall()}

        missing = [c for c in wanted if c not in known]
        wanted = {c: k for c, k in wanted.items() if c in known}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not args.dry_run:
            with conn.cursor() as cur:
                for cid, kws in wanted.items():
                    for kid, term in kws.items():
                        cur.execute(
                            f"""INSERT INTO `{db.LINKS_TABLE}`
                                  (keyword_id, keyword, chart_id, record_timestamp,
                                   source, matched_in)
                                VALUES (%s, %s, %s, %s, 'ai', 'page-text')
                                ON DUPLICATE KEY UPDATE keyword = VALUES(keyword),
                                  source = 'ai', matched_in = 'page-text'""",
                            (kid, term, cid, now))
                # keep the chart's own keyword array in step with the links
                for cid in wanted:
                    cur.execute(f"""SELECT keyword FROM `{db.LINKS_TABLE}`
                                     WHERE chart_id = %s""", (cid,))
                    terms = sorted({r[0] for r in cur.fetchall()})
                    cur.execute(f"UPDATE `{db.CHARTS_TABLE}` SET keywords = %s "
                                f"WHERE chart_id = %s",
                                (json.dumps(terms, ensure_ascii=False), cid))
            conn.commit()

        links = sum(len(v) for v in wanted.values())
        if args.quiet:
            print(f"AI keywords: {links} link(s) over {len(wanted)} chart(s)"
                  + (f" | {sum(dropped.values())} dropped as rejected terms" if dropped else "")
                  + ("  [dry run]" if args.dry_run else ""))
            return 0

        print(f"{'[dry run] ' if args.dry_run else ''}"
              f"{links} ai link(s) over {len(wanted)} chart(s)")
        if missing:
            print(f"  {len(missing)} chart(s) in the state file are no longer in the gallery")
        if dropped:
            print("  dropped — the vocabulary no longer carries these terms:")
            for term, n in dropped.most_common():
                print(f"    {n:>3}  {term}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
