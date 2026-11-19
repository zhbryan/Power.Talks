#!/usr/bin/env python3
"""build_keywords_json.py — mirror the curated vocabulary into JSON.

Reads `ercot_keyword_vocabulary.yaml` (the hand-authored source of truth) and
writes `ercot_market_keywords.json` beside it, for everything downstream: the
`gallery.keyword_id` table (via sync_keyword_ids.py), the GALLERY chart
extractor's closed vocabulary, and the Gallery page's keyword search.

    py -3 "Database Codes/reference_info/build_keywords_json.py"
    py -3 "Database Codes/reference_info/build_keywords_json.py" --quiet

Until 2026-11-19 this script parsed `ercot_market_keywords.md`. That file is
now narrative only — a readable tour of what the market is talking about — and
is no longer machine-read, because a bullet list cannot express the aliases,
glossary citations, scope notes and hierarchy the vocabulary needs. The YAML
carries those, and `validate_vocabulary.py` enforces them. This script refuses
to write if validation would fail, so a broken vocabulary can never reach the
database.

`keyword_id` is a stable 12-hex-char digest of the normalized term, so rows in
`gallery.keyword_id` survive a nightly rebuild (see vocabulary.keyword_id).

Schema:
    {
      "source", "compiled_at", "version", "count", "trending_count",
      "categories": [facet label, ...],
      "rules": {...},            # matching rules the extractor must honour
      "blocklist": [...],        # surface forms too broad to match on
      "keywords": [
        {"keyword_id","term","acronym","category","description","trending",
         "facet","broader","glossary_ref","extension_reason","scope_note",
         "status","aliases":[...],"match_forms":[...],"replaces":[...]}, ...
      ],
      "rejected": [{"term","reason"}, ...]
    }
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vocabulary as V  # noqa: E402

OUT = os.path.join(HERE, "ercot_market_keywords.json")
VALIDATOR = os.path.join(HERE, "validate_vocabulary.py")


def glossary_definitions(path=V.GLOSSARY_JSON):
    """term_s -> plain-text definition, for filling `description`."""
    with open(path, encoding="utf-8") as f:
        terms = json.load(f)["terms"]
    out = {}
    for e in terms:
        t = re.sub(r"\s+", " ", (e.get("term_s") or "").strip())
        if not t:
            continue
        d = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", e.get("definition_html_raw") or ""))
        d = (d.replace("&rsquo;", "’").replace("&ldquo;", "“")
              .replace("&rdquo;", "”").replace("&amp;", "&").strip())
        if d:
            out[t] = d
    return out


def first_sentence(text, limit=240):
    t = re.sub(r"\s+", " ", text or "").strip()
    m = re.search(r"(?<=[.;])\s", t)
    if m and m.start() <= limit:
        t = t[:m.start()]
    return t[:limit].rstrip(" ,;:")


def describe(c, defs):
    """One line for the keyword's tooltip in the Gallery picker."""
    if c.scope_note:
        return first_sentence(c.scope_note)
    if c.glossary_ref and c.glossary_ref in defs:
        return first_sentence(defs[c.glossary_ref])
    if c.extension_reason:
        return first_sentence(c.extension_reason)
    return c.term


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="one summary line (nightly / headless)")
    ap.add_argument("--skip-validate", action="store_true",
                    help="write even if the vocabulary fails validation (not for the routine)")
    args = ap.parse_args()

    # The vocabulary is the gate: nothing reaches the database unvalidated.
    if not args.skip_validate:
        r = subprocess.run([sys.executable, VALIDATOR, "--quiet", "--no-db"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            sys.stderr.write("\nbuild_keywords_json: refusing to write — "
                             "fix the vocabulary first.\n")
            return 1

    vocab = V.load()
    defs = glossary_definitions()

    keywords = []
    for c in vocab.concepts:
        if c.status == "retired":
            continue
        forms = sorted(c.match_forms(vocab.blocklist, vocab.min_alias_length,
                                     vocab.min_acronym_length))
        keywords.append({
            "keyword_id": c.keyword_id,
            "term": c.term,
            "acronym": c.acronym,
            "category": vocab.facets.get(c.facet, c.facet),
            "description": describe(c, defs),
            "trending": c.trending,
            "facet": c.facet,
            "broader": c.broader,
            "glossary_ref": c.glossary_ref,
            "extension_reason": c.extension_reason,
            "scope_note": c.scope_note,
            "status": c.status,
            "aliases": list(c.aliases),
            "match_forms": forms,
            "replaces": list(c.replaces),
        })

    data = {
        "source": os.path.basename(vocab.path),
        "compiled_at": str(vocab.compiled),
        "version": vocab.version,
        "count": len(keywords),
        "trending_count": sum(1 for k in keywords if k["trending"]),
        "categories": [vocab.facets[f] for f in vocab.facets],
        "rules": {
            "min_alias_length": vocab.min_alias_length,
            "min_acronym_length": vocab.min_acronym_length,
            "qualifying_fields": list(vocab.qualifying_fields),
            "weak_fields": list(vocab.weak_fields),
            "max_keywords_per_chart": vocab.max_keywords_per_chart,
        },
        "blocklist": sorted(vocab.blocklist),
        "keywords": keywords,
        "rejected": [{"term": str(r.get("term", "")),
                      "reason": re.sub(r"\s+", " ", str(r.get("reason", ""))).strip()}
                     for r in vocab.rejected],
    }

    prev = None
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                prev = json.load(f)
        except Exception:
            prev = None

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    active = sum(1 for k in keywords if k["status"] == "active")
    forms = sum(len(k["match_forms"]) for k in keywords)
    if args.quiet:
        delta = ""
        if prev:
            before = {k["term"] for k in prev.get("keywords", [])}
            now = {k["term"] for k in keywords}
            added, gone = len(now - before), len(before - now)
            delta = f" | +{added} -{gone}" if (added or gone) else " | no changes"
        print(f"Market keywords: {len(keywords)} concepts ({active} active), "
              f"{forms} surface forms{delta}")
    else:
        print(f"Wrote {OUT}")
        print(f"  {len(keywords)} concepts: {active} active, "
              f"{len(keywords) - active} candidate")
        print(f"  {data['trending_count']} trending | {forms} surface forms")
        print(f"  {sum(1 for k in keywords if k['glossary_ref'])} glossary-anchored, "
              f"{sum(1 for k in keywords if not k['glossary_ref'])} declared extensions")
        print(f"  {len(data['rejected'])} rejected terms recorded")
        if prev:
            before = {k["term"] for k in prev.get("keywords", [])}
            now = {k["term"] for k in keywords}
            for t in sorted(now - before):
                print(f"    + {t}")
            for t in sorted(before - now):
                print(f"    - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
