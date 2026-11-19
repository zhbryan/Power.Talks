#!/usr/bin/env python3
"""propose_keywords.py — what the gallery is about that the vocabulary cannot name.

    py -3 propose_keywords.py                 # full report
    py -3 propose_keywords.py --quiet         # one line (nightly / headless)
    py -3 propose_keywords.py --min 8 --top 40

Vocabulary growth is evidence-driven and human-approved: this script never
edits anything. It reads the charts that carry no keyword, finds the phrases
that recur across them, drops anything the vocabulary already matches or has
deliberately blocked or rejected, and ranks what is left by how many charts it
would reach. A phrase that appears on dozens of charts and has no concept is
the vocabulary's blind spot; one that appears twice is noise.

Promoting a proposal means adding a concept to `ercot_keyword_vocabulary.yaml`
by hand -- with a scope note, a glossary citation or a stated reason for not
having one, and aliases -- then running build / sync / retag. That deliberate
step is the point: a vocabulary that grows itself grows redundant.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vocabulary as V  # noqa: E402

DB_CONFIG = os.path.join(HERE, "..", "ercot_api", "db_config.json")

# Words that carry no subject on their own. Beyond the vocabulary's own
# blocklist: these are the scaffolding of chart titles.
NOISE = set("""the a an of and or for to in on by with at from vs versus per as is are was
were be been this that these those it its no not all any each other more most new
report reports update updates summary presentation slide slides chart charts figure
table data analysis overview comparison comparisons total totals average averages
monthly annual daily hourly weekly yearly year years month months day days hour hours
january february march april may june july august september october november december
summer winter spring fall final draft revised version preliminary actual estimated
percent percentage number numbers value values trend trends top bottom high low max min
north south east west central houston coastal panhandle system wide systemwide
ercot texas page sheet tab copy xlsx xls pdf""".split())


def phrases(text, n):
    words = [w for w in re.sub(r"[^A-Za-z0-9\-/+ ]", " ", text or "").lower().split()
             if w not in NOISE and len(w) > 2 and not w.replace("-", "").isdigit()]
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min", type=int, default=5, help="minimum charts a proposal must reach")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    vocab = V.load()
    known = set(vocab.form_index())
    rejected = {V.norm(str(r.get("term", ""))) for r in vocab.rejected}

    import pymysql
    with open(DB_CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    conn = pymysql.connect(host=cfg["host"], port=int(cfg["port"]), user=cfg["user"],
                           password=cfg["password"], database="gallery", charset="utf8mb4")
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM gallery_charts")
        total = cur.fetchone()[0]
        cur.execute("""SELECT c.chart_id, COALESCE(c.chart_title,''), c.doc_name,
                              COALESCE(c.page_num,''), c.doc_group
                         FROM gallery_charts c
                         LEFT JOIN gallery_keywords g ON g.chart_id = c.chart_id
                        WHERE g.chart_id IS NULL""")
        rows = cur.fetchall()
    conn.close()

    counts = collections.Counter()
    groups = collections.defaultdict(collections.Counter)
    for cid, title, doc, page, group in rows:
        text = f"{title} {page}"
        seen = set()
        for n in (3, 2, 1):
            seen |= phrases(text, n)
        for p in seen:
            if p in known or p in rejected or V.norm(p) in vocab.blocklist:
                continue
            counts[p] += 1
            groups[p][group] += 1

    # Drop a phrase that is wholly inside a longer phrase scoring just as well:
    # "profile type volumes" and "profile type" should not both be proposed.
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    kept = []
    for phrase, n in ranked:
        if n < args.min:
            continue
        if any(phrase != o and phrase in o and counts[o] >= n * 0.9 for o, _ in kept):
            continue
        kept.append((phrase, n))

    if args.quiet:
        reach = len({r[0] for r in rows})
        print(f"Keyword proposals: {len(kept)} phrase(s) >= {args.min} charts, "
              f"over {reach} untagged chart(s) of {total}")
        return 0

    print(f"{len(rows)} of {total} charts carry no keyword "
          f"({len(rows)/max(total,1):.0%})\n")
    if not kept:
        print("No recurring phrase above the threshold — the vocabulary covers "
              "what the untagged charts say.")
        return 0

    print(f"Phrases on >= {args.min} untagged charts that no concept matches.")
    print("Promote one by adding a concept to ercot_keyword_vocabulary.yaml.\n")
    print(f"  {'charts':>6}  {'phrase':<44}  mostly from")
    for phrase, n in kept[:args.top]:
        top = ", ".join(f"{g}({c})" for g, c in groups[phrase].most_common(2))
        print(f"  {n:>6}  {phrase:<44}  {top}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
