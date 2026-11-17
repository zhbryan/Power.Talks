#!/usr/bin/env python3
"""build_gallery_index.py - build/refresh the GALLERY chart index.

`Documents Database/GALLERY/gallery_index.json` is the curated source of truth
for the extracted chart images: one record per PNG with its title, chart type,
originating document/page, and keywords. This script is the mechanical half --
it re-links every keyword to the ERCOT reference files so the web Gallery page
can show (and search on) authoritative definitions:

    Database Codes/reference_info/ercot_glossary.json         (official ERCOT terms)
    Database Codes/reference_info/ercot_market_keywords.json  (curated market vocabulary)

Run it after editing the index or after either reference file is regenerated:

    py -3 "Database Codes/build_gallery_index.py"
    py -3 "Database Codes/build_gallery_index.py" --quiet

Curated fields (title, chart_type, source_pdf, source_page, keywords) are never
overwritten. PNGs in GALLERY with no record are reported as untracked; records
whose file is missing from disk are reported as orphaned.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALLERY = os.path.join(ROOT, "Documents Database", "GALLERY")
INDEX = os.path.join(GALLERY, "gallery_index.json")
GLOSSARY = os.path.join(ROOT, "Database Codes", "reference_info", "ercot_glossary.json")
KEYWORDS = os.path.join(ROOT, "Database Codes", "reference_info", "ercot_market_keywords.json")

_TAGS = re.compile(r"<[^>]+>")
_PARENS = re.compile(r"\s*\([^()]*\)\s*$")


def _norm(s):
    return re.sub(r"[^a-z0-9+ ]", " ", s.lower()).strip()


def _squash(s):
    return re.sub(r"\s+", " ", s).strip()


def load_glossary():
    """-> {normalized term: {"term","definition"}} including acronym aliases."""
    with open(GLOSSARY, encoding="utf-8") as f:
        terms = json.load(f)["terms"]
    out = {}
    for t in terms:
        term = _squash(t.get("term_s", ""))
        if not term:
            continue
        definition = _squash(_TAGS.sub(" ", t.get("definition_html_raw", "")))
        rec = {"term": term, "definition": definition}
        out.setdefault(_norm(term), rec)
        # "Adjusted Metered Load (AML)" -> also index "Adjusted Metered Load" and "AML"
        m = re.search(r"\(([^()]+)\)\s*$", term)
        if m:
            out.setdefault(_norm(m.group(1)), rec)
            out.setdefault(_norm(_PARENS.sub("", term)), rec)
    return out


def load_keywords():
    """-> {normalized term: {"term","category","description"}} + acronym aliases."""
    with open(KEYWORDS, encoding="utf-8") as f:
        kws = json.load(f)["keywords"]
    out = {}
    for k in kws:
        term = _squash(k["term"])
        rec = {"term": term, "category": k.get("category", ""),
               "description": k.get("description", "")}
        out.setdefault(_norm(term), rec)
        out.setdefault(_norm(_PARENS.sub("", term)), rec)
        if k.get("acronym"):
            for tok in re.split(r"[/,]", k["acronym"]):
                tok = tok.strip()
                if tok:
                    out.setdefault(_norm(tok), rec)
    return out


def _hit(rec, source, how):
    out = {"source": source, "matched_term": rec["term"], "match": how}
    if source == "ercot_glossary":
        out["definition"] = rec["definition"]
    else:
        out["category"] = rec["category"]
        out["description"] = rec["description"]
    return out


def link(keyword, glossary, keywords, aliases=None):
    """Resolve one keyword against the reference files, strictest first:

      1. exact (normalized) match, the keyword also tried without a trailing
         parenthetical and as the acronym inside it;
      2. an explicit alias from the index's "aliases" map;
      3. whole-word prefix -- the keyword is the opening words of a longer
         reference term ("shoulder season" -> "Shoulder season outage
         scheduling"), which is unambiguous only if exactly one term matches.

    Anything looser is left unlinked: a wrong definition on the Gallery page is
    worse than no definition."""
    cands = [keyword, _PARENS.sub("", keyword)]
    m = re.search(r"\(([^()]+)\)", keyword)
    if m:
        cands.append(m.group(1))
    if aliases and keyword in aliases:
        cands.append(aliases[keyword])

    for c in cands:
        n = _norm(c)
        if n in glossary:
            return _hit(glossary[n], "ercot_glossary",
                        "exact" if c == keyword else "alias")
    for c in cands:
        n = _norm(c)
        if n in keywords:
            return _hit(keywords[n], "ercot_market_keywords",
                        "exact" if c == keyword else "alias")

    n = _norm(keyword)
    for store, src in ((keywords, "ercot_market_keywords"), (glossary, "ercot_glossary")):
        hits = {r["term"]: r for k, r in store.items() if k.startswith(n + " ")}
        if len(hits) == 1:
            return _hit(next(iter(hits.values())), src, "prefix")
    return {"source": None}


def canonicalize(data):
    """Collapse synonym keywords onto their generic term and drop chart-form
    words (those belong in each image's `chart_type`, not in its keywords).

    Returns (folds, strips) as lists of (file, before, after) / (file, term).
    Order is preserved and duplicates created by a fold are removed."""
    block = data.get("canonicalization") or {}
    syn = {k.lower(): v for k, v in (block.get("synonyms") or {}).items()}
    form = {t.lower() for t in (block.get("chart_form_terms") or [])}
    folds, strips = [], []
    for img in data.get("images", []):
        out = []
        for kw in img.get("keywords", []):
            low = kw.lower()
            if low in form:
                strips.append((img["file"], kw))
                continue
            canon = syn.get(low, kw)
            if canon != kw:
                folds.append((img["file"], kw, canon))
            if canon not in out:
                out.append(canon)
        img["keywords"] = out
    return folds, strips


def main():
    quiet = "--quiet" in sys.argv
    if not os.path.exists(INDEX):
        print(f"ERROR: {INDEX} not found - create the curated index first.", file=sys.stderr)
        return 1
    with open(INDEX, encoding="utf-8") as f:
        data = json.load(f)

    glossary, keywords = load_glossary(), load_keywords()

    # Canonicalize first: similar keywords must be represented by one generic
    # term, so the same idea is not split across near-duplicate strings in
    # search. Rewritten in place, so the curated file self-heals.
    folded, stripped = canonicalize(data)

    linked = unlinked = 0
    for img in data.get("images", []):
        links = []
        for kw in img.get("keywords", []):
            r = link(kw, glossary, keywords, data.get("aliases"))
            r["keyword"] = kw
            links.append(r)
            if r["source"]:
                linked += 1
            else:
                unlinked += 1
        img["keyword_links"] = links
        img["file_exists"] = os.path.exists(os.path.join(GALLERY, img["file"]))

    data["linked_at"] = __import__("datetime").date.today().isoformat()
    data["link_stats"] = {"linked": linked, "unlinked": unlinked}
    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    tracked = {i["file"] for i in data.get("images", [])}
    on_disk = {f for f in os.listdir(GALLERY) if f.lower().endswith(".png")}
    untracked = sorted(on_disk - tracked)
    orphaned = [i["file"] for i in data.get("images", []) if not i["file_exists"]]
    n = len(data.get("images", []))
    if quiet:
        # one line for the nightly log, matching the other routine steps
        warn = ""
        if untracked:
            warn += f" | {len(untracked)} untracked PNG(s)"
        if orphaned:
            warn += f" | {len(orphaned)} orphaned record(s)"
        if folded or stripped:
            warn += f" | {len(folded)} folded, {len(stripped)} form-word(s) dropped"
        print(f"Gallery index: {n} images, {linked} linked / {unlinked} unlinked{warn}")
    else:
        print(f"Wrote {INDEX}")
        print(f"  {n} images, {linked} keywords linked, {unlinked} unlinked.")
        for f, before, after in folded:
            print(f"  FOLDED  {before!r} -> {after!r}  ({f})")
        for f, term in stripped:
            print(f"  DROPPED {term!r} (chart form, see chart_type)  ({f})")
        for f in untracked:
            print(f"  UNTRACKED (no index record): {f}")
        for f in orphaned:
            print(f"  ORPHANED (file missing from disk): {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
