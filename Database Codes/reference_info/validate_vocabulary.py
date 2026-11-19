#!/usr/bin/env python3
"""validate_vocabulary.py — enforce the three laws of the keyword vocabulary.

    py -3 "Database Codes/reference_info/validate_vocabulary.py"
    py -3 "Database Codes/reference_info/validate_vocabulary.py" --quiet
    py -3 "Database Codes/reference_info/validate_vocabulary.py" --no-db

ERRORS fail the run (exit 1) and must be fixed in the YAML. WARNINGS are
reported and do not fail — they are judgement calls for a human, chiefly the
behavioural-redundancy pairs, where only a person can say whether two concepts
that happen to tag the same charts today are really the same subject.

Law 1  generic only     — no bill, revision request, year, month, threshold or
                          named project in a term or an alias.
Law 2  one concept      — no term joins two ideas; every alias means the same
                          thing as its concept.
Law 3  no overlap       — no term's words contain another's, no alias is
                          claimed twice, and no two concepts tag substantially
                          the same charts.
"""
import argparse
import collections
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vocabulary as V  # noqa: E402

DB_CONFIG = os.path.join(HERE, "..", "ercot_api", "db_config.json")
STOP_WORDS = {"and", "or", "of", "the", "in", "to", "for", "a", "by", "on"}


def term_tokens(term):
    base = V.strip_parens(term)
    return {w for w in V.norm(base).split() if w not in STOP_WORDS}


def chart_sets():
    """keyword_id -> set(chart_id) from the live gallery, or None if unreachable."""
    try:
        import pymysql
        with open(DB_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        conn = pymysql.connect(host=cfg["host"], port=int(cfg["port"]), user=cfg["user"],
                               password=cfg["password"], database="gallery",
                               charset="utf8mb4", connect_timeout=5)
        with conn.cursor() as cur:
            cur.execute("SELECT keyword_id, chart_id FROM gallery_keywords")
            out = collections.defaultdict(set)
            for kid, cid in cur.fetchall():
                out[kid].add(cid)
        conn.close()
        return out
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="one summary line unless something fails")
    ap.add_argument("--no-db", action="store_true", help="skip the behavioural-redundancy check")
    args = ap.parse_args()

    vocab = V.load()
    gloss_forms = V.load_glossary()
    gloss_exact = V.glossary_terms()

    errors, warnings = [], []

    def err(c, msg):
        errors.append((c.term if c else "(file)", msg))

    def warn(c, msg):
        warnings.append((c.term if c else "(file)", msg))

    # ── structure ────────────────────────────────────────────────────────────
    seen_terms, seen_ids = {}, {}
    for c in vocab.concepts:
        if not c.term:
            err(None, "a concept has no term")
            continue
        if c.status not in V.STATUSES:
            err(c, f"status {c.status!r} is not one of {V.STATUSES}")
        if c.facet not in vocab.facets:
            err(c, f"facet {c.facet!r} is not declared in facets:")
        if V.norm(c.term) in seen_terms:
            err(c, "duplicate term")
        seen_terms[V.norm(c.term)] = c
        if c.keyword_id in seen_ids:
            err(c, f"keyword_id collides with {seen_ids[c.keyword_id].term!r}")
        seen_ids[c.keyword_id] = c
        if not c.glossary_ref and not c.extension_reason:
            err(c, "no glossary_ref and no extension_reason — one is required")
        if c.glossary_ref and c.glossary_ref not in gloss_exact:
            err(c, f"glossary_ref {c.glossary_ref!r} is not a term in the ERCOT glossary")
        if c.broader and V.norm(c.broader) not in {V.norm(x.term) for x in vocab.concepts}:
            err(c, f"broader {c.broader!r} is not a concept in this file")

    # ── law 1: generic only ──────────────────────────────────────────────────
    for c in vocab.concepts:
        for text, where in [(c.term, "term")] + [(a, "alias") for a in c.aliases]:
            for rx, why in V.INSTANCE_PATTERNS:
                if rx.search(str(text)):
                    err(c, f"law 1: {where} {text!r} {why}")

    # ── law 2: one concept per term ──────────────────────────────────────────
    for c in vocab.concepts:
        if " / " in V.strip_parens(c.term):
            err(c, "law 2: term joins two concepts with '/' — split it")
        for a in c.aliases:
            if " / " in V.strip_parens(str(a)):
                err(c, f"law 2: alias {a!r} joins two concepts with '/'")

    # ── law 3a: no alias claimed by two concepts ─────────────────────────────
    for form, owners in vocab.form_index().items():
        if len(owners) > 1:
            err(owners[0], "law 3: surface form {!r} is also claimed by {}".format(
                form, ", ".join(repr(o.term) for o in owners[1:])))

    # ── law 3b: no term's words contain another's ────────────────────────────
    for a, b in itertools.combinations(vocab.concepts, 2):
        ta, tb = term_tokens(a.term), term_tokens(b.term)
        if not ta or not tb or ta == tb:
            continue
        if ta < tb or tb < ta:
            parent, child = (a, b) if ta < tb else (b, a)
            if V.norm(child.broader or "") == V.norm(parent.term):
                continue            # an explicit hierarchy, not an accident
            err(child, f"law 3: term overlaps {parent.term!r} "
                       f"(declare `broader: {parent.term}` if that is the relation)")

    # ── alias hygiene ────────────────────────────────────────────────────────
    for c in vocab.concepts:
        for a in c.aliases:
            n = V.norm(str(a))
            if not n:
                err(c, f"alias {a!r} normalizes to nothing")
            elif n in vocab.blocklist:
                err(c, f"alias {a!r} is on the blocklist — too broad to match on")
            else:
                floor = V.form_min_length(a, vocab.min_alias_length, vocab.min_acronym_length)
                if len(n) < floor:
                    kind = "min_acronym_length" if V.is_acronym(a) else "min_alias_length"
                    err(c, f"alias {a!r} is shorter than {kind} ({len(n)} < {floor})")
        if c.status != "retired" and not c.match_forms(
                vocab.blocklist, vocab.min_alias_length, vocab.min_acronym_length):
            err(c, "no usable surface form — every form is blocked or too short")

    # ── replaces: must not point at a live term ──────────────────────────────
    for c in vocab.concepts:
        for old in c.replaces:
            if V.norm(old) in seen_terms and V.norm(old) != V.norm(c.term):
                err(c, f"replaces {old!r}, which is still a live term")

    # ── glossary coverage (reporting, not a rule) ────────────────────────────
    anchored = sum(1 for c in vocab.concepts if c.glossary_ref)
    for c in vocab.concepts:
        if not c.glossary_ref:
            hit = gloss_forms.get(V.norm(V.strip_parens(c.term)))
            if hit:
                warn(c, f"declares no glossary_ref but the glossary has {hit!r}")

    # ── law 3c: behavioural redundancy, from the live gallery ────────────────
    sets = None if args.no_db else chart_sets()
    redundant = []
    if sets:
        jt = float(vocab.rules.get("redundancy_jaccard", 0.60))
        ct = float(vocab.rules.get("redundancy_containment", 0.90))
        min_charts = int(vocab.rules.get("redundancy_min_charts", 10))
        live = [c for c in vocab.concepts if len(sets.get(c.keyword_id, ())) >= 3]
        for a, b in itertools.combinations(live, 2):
            A, B = sets[a.keyword_id], sets[b.keyword_id]
            inter = len(A & B)
            if not inter:
                continue
            j = inter / len(A | B)
            cov = max(inter / len(A), inter / len(B))
            if j >= jt or (cov >= ct and min(len(A), len(B)) >= min_charts):
                redundant.append((j, cov, a, b))
                warn(a, f"law 3: tags {cov:.0%} of the same charts as {b.term!r} "
                        f"(jaccard {j:.2f}) — merge, or give one a narrower scope_note")

    # ── report ───────────────────────────────────────────────────────────────
    by_status = collections.Counter(c.status for c in vocab.concepts)
    # Status is authored intent; this says what the gallery actually supports
    # today, so an "active" list cannot quietly drift from the evidence.
    idle_active = None
    if sets is not None:
        idle_active = sum(1 for c in vocab.concepts
                          if c.status == "active" and not sets.get(c.keyword_id))
    if not args.quiet:
        print(f"Vocabulary {vocab.path}")
        print(f"  version {vocab.version}, compiled {vocab.compiled}")
        print(f"  {len(vocab.concepts)} concepts: "
              + ", ".join(f"{n} {s}" for s, n in sorted(by_status.items())))
        print(f"  glossary-anchored {anchored}/{len(vocab.concepts)}; "
              f"{len(vocab.concepts) - anchored} declared extensions")
        if idle_active:
            print(f"  {idle_active} active concept(s) currently match no chart "
                  f"(vocabulary ahead of the corpus, not an error)")
        print(f"  {len(vocab.rejected)} rejected terms recorded")
        print(f"  {sum(len(c.match_forms(vocab.blocklist, vocab.min_alias_length)) for c in vocab.concepts)}"
              f" surface forms, {len(vocab.blocklist)} blocked")
        bf = collections.Counter(c.facet for c in vocab.concepts)
        for f, label in vocab.facets.items():
            print(f"    {bf.get(f, 0):>3}  {label}")
        if sets is None and not args.no_db:
            print("  (gallery not reachable — behavioural redundancy not checked)")
        print()

    for term, msg in warnings:
        print(f"WARN  {term}: {msg}")
    for term, msg in errors:
        print(f"ERROR {term}: {msg}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    if args.quiet:
        print(f"Vocabulary: {len(vocab.concepts)} concepts "
              f"({by_status.get('active', 0)} active, {by_status.get('candidate', 0)} candidate) "
              f"| {anchored} glossary-anchored | {len(warnings)} warning(s)")
    else:
        print(f"OK — {len(vocab.concepts)} concepts, 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
