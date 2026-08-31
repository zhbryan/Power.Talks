"""glossary_reference.py — shared ERCOT terminology reference for the summarizers.

Builds a cached Anthropic `system` block from the glossary that
`update_ercot_glossary.py` writes (Database Codes/reference_info/ercot_glossary.json),
so the AI expands acronyms and explains terms using ERCOT's OFFICIAL definitions
instead of guessing — e.g. RMR = "Reliability Must-Run", never "Reserve Margin".

Usage in a summarizer:

    import glossary_reference
    _SYS_KW = glossary_reference.system_kwargs()      # {} if glossary unavailable
    ...
    get_ai().messages.create(model=AI_MODEL, max_tokens=AI_MAX_TOKENS,
                             **_SYS_KW, messages=[...])

The block carries `cache_control` so, across the many summary calls in a run, the
large glossary prefix is written once and read cheaply thereafter. Degrades to an
empty dict when the glossary file is missing, so summaries still run without it.
"""

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GLOSSARY_JSON = os.path.join(HERE, "..", "reference_info", "ercot_glossary.json")

_ACRONYM_RE = re.compile(r"^[A-Z0-9]{2,8}$")
_TAG_RE = re.compile(r"<[^>]+>")
_FIRST_BREAK_RE = re.compile(r"(?i)</p>|<br\s*/?>|</li>|\n")

_cache = "__unset__"   # sentinel: not yet built


def _plain(defn_html):
    """Flatten a definition's HTML to single-line plain text."""
    t = _TAG_RE.sub(" ", html.unescape(defn_html or ""))
    return re.sub(r"\s+", " ", t).strip()


def _first_line(defn_html):
    """Text of the first paragraph/line — the acronym's expansion."""
    return _plain(_FIRST_BREAK_RE.split(defn_html or "", 1)[0])


def _build_text(terms):
    acr_lines, full_lines = [], []
    for t in terms:
        term = (t.get("term_s") or "").strip()
        if not term:
            continue
        defn = _plain(t.get("definition_html_raw"))
        full_lines.append(f"{term}: {defn}" if defn else term)
        if _ACRONYM_RE.match(term):
            exp = _first_line(t.get("definition_html_raw"))
            acr_lines.append(f"{term} = {exp}" if exp else term)
    acr_lines = sorted(set(acr_lines))
    full_lines.sort(key=str.lower)
    return (
        "You are summarizing ERCOT power-system, grid, and market-operations "
        "documents. When you expand an acronym or explain an ERCOT term, use ONLY "
        "the official ERCOT definitions below. NEVER invent an acronym expansion. "
        "For example, \"RMR\" means \"Reliability Must-Run\" (NOT \"Reserve "
        "Margin\"). If a term is not listed and you are not certain of its meaning, "
        "keep the acronym as-is rather than guessing.\n\n"
        "=== KEY ERCOT ACRONYMS ===\n" + "\n".join(acr_lines) +
        "\n\n=== FULL ERCOT GLOSSARY ===\n" + "\n".join(full_lines)
    )


def terminology_system():
    """Anthropic `system` value (list with one cached text block) built from the
    ERCOT glossary, or None if the glossary file isn't available."""
    global _cache
    if _cache != "__unset__":
        return _cache
    try:
        with open(GLOSSARY_JSON, encoding="utf-8") as f:
            terms = json.load(f).get("terms", [])
    except (OSError, ValueError):
        terms = []
    _cache = ([{"type": "text", "text": _build_text(terms),
                "cache_control": {"type": "ephemeral"}}] if terms else None)
    return _cache


def system_kwargs():
    """`{"system": [...]}` to splat into messages.create(), or `{}` if unavailable."""
    s = terminology_system()
    return {"system": s} if s else {}
