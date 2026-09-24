#!/usr/bin/env python3
"""build_keywords_json.py — regenerate the machine-readable companion for the
ERCOT market keyword list.

Parses the curated `ercot_market_keywords.md` (the human-authored source of
truth) and writes `ercot_market_keywords.json` alongside it, so downstream code
(Hot Topics ranking, search, the AI pipeline) can consume the list structurally.

The Markdown is the authored artifact; this script never edits it — it only
mirrors it into JSON. Run it after every edit to the .md:

    py -3 "Database Codes/reference_info/build_keywords_json.py"          # build + report
    py -3 "Database Codes/reference_info/build_keywords_json.py" --quiet  # nightly / headless

Schema:
    {
      "source": "...", "compiled_at": "YYYY-MM-DD",
      "count": N, "trending_count": T,
      "categories": ["Market design & structure", ...],
      "keywords": [
        {"term","acronym"|null,"category","description","trending"}, ...
      ]
    }
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "ercot_market_keywords.md")
OUT = os.path.join(HERE, "ercot_market_keywords.json")

# Section headings that are NOT keyword categories.
SKIP_HEADINGS = ("Trending now", "Quick-reference acronyms", "Sources")

_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")      # markdown link -> its text
_BOLD = re.compile(r"^\*\*(.+?)\*\*(.*)$")         # **Term**<rest>
_ACRONYM_TAIL = re.compile(r"\(([^()]+)\)\s*$")    # trailing (...) on the term


def _clean(s):
    return re.sub(r"\s+", " ", _LINK.sub(r"\1", s)).strip()


def parse():
    with open(MD, encoding="utf-8") as f:
        lines = f.read().splitlines()

    compiled = ""
    for ln in lines:
        m = re.match(r"-\s*\*\*Compiled:\*\*\s*(\S+)", ln)
        if m:
            compiled = m.group(1)
            break

    # Trending labels come from the "🔥 Trending now" table (first column).
    trending_keys = set()
    in_trending = False
    for ln in lines:
        if ln.startswith("## "):
            in_trending = "Trending now" in ln
            continue
        if in_trending:
            m = re.match(r"\|\s*\*\*(.+?)\*\*\s*\|", ln)
            if m:
                label = _clean(m.group(1))
                # 1. acronyms inside parentheses, e.g. (RTC+B), (Reg-Up / Reg-Down)
                am = re.search(r"\(([^()]+)\)", label)
                if am:
                    for tok in re.split(r"[/,]", am.group(1)):
                        trending_keys.add(tok.strip().lower())
                # 2. standalone uppercase acronym tokens in the label text (ESR, SOC…)
                for tok in re.findall(r"\b[A-Z][A-Z0-9+]{1,}\b", label):
                    trending_keys.add(tok.lower())
                # 3. each slash/comma-separated phrase (parens stripped), e.g.
                #    "Large loads / data centers" -> "large loads", "data centers"
                bare = re.sub(r"\([^()]*\)", "", label)
                for phrase in re.split(r"[/,]", bare):
                    p = phrase.strip().lower()
                    if p:
                        trending_keys.add(p)

    def is_trending(term, acronym):
        t = term.lower()
        if acronym and acronym.lower() in trending_keys:
            return True
        for k in trending_keys:
            if len(k) >= 4 and k in t:
                return True
        return False

    keywords, categories = [], []
    category = None
    for ln in lines:
        h = re.match(r"##\s+(?:\d+\.\s*)?(.+)$", ln)
        if h:
            name = _clean(re.sub(r"^[^\w]+", "", h.group(1)))
            if any(s in name for s in SKIP_HEADINGS):
                category = None
            else:
                category = name
                categories.append(name)
            continue
        if not category:
            continue
        b = re.match(r"-\s+(.*)$", ln)
        if not b:
            continue
        body = _clean(b.group(1))
        mb = _BOLD.match(body)
        if mb:
            term_raw = mb.group(1).strip()
            rest = mb.group(2)
        else:
            term_raw, rest = body, ""
        # description: text after an em/en dash separator
        desc = ""
        dm = re.search(r"[—–-]\s+(.*)$", rest)
        if dm:
            desc = _clean(dm.group(1))
        # acronym: trailing (...) if it reads like an abbreviation set
        acronym = None
        am = _ACRONYM_TAIL.search(term_raw)
        if am and len(am.group(1)) <= 40:
            acronym = am.group(1).strip()
        keywords.append({
            "term": term_raw,
            "acronym": acronym,
            "category": category,
            "description": desc,
            "trending": is_trending(term_raw, acronym),
        })

    return compiled, categories, keywords


def main():
    quiet = "--quiet" in sys.argv
    compiled, categories, keywords = parse()
    data = {
        "source": "Curated from ERCOT.com, PUCT filings, and analyst/trade research "
                  "(see Sources in ercot_market_keywords.md)",
        "compiled_at": compiled,
        "count": len(keywords),
        "trending_count": sum(1 for k in keywords if k["trending"]),
        "categories": categories,
        "keywords": keywords,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if not quiet:
        print(f"Wrote {OUT}")
        print(f"  {data['count']} keywords across {len(categories)} categories, "
              f"{data['trending_count']} flagged trending.")


if __name__ == "__main__":
    main()
