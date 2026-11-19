#!/usr/bin/env python3
"""vocabulary.py — shared reader for `ercot_keyword_vocabulary.yaml`.

One implementation of the things that must agree everywhere: how a term is
normalized, how its id is derived, and which surface forms may match text.
`build_keywords_json.py`, `validate_vocabulary.py`, `sync_keyword_ids.py` and
the GALLERY extractor all go through here, so a change to the matching rules
cannot drift between the web page, the nightly routine and the validator.
"""
import hashlib
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB_YAML = os.path.join(HERE, "ercot_keyword_vocabulary.yaml")
GLOSSARY_JSON = os.path.join(HERE, "ercot_glossary.json")

STATUSES = ("active", "candidate", "retired")

# A term that names one instance instead of a concept. Law 1 of the vocabulary.
INSTANCE_PATTERNS = [
    (re.compile(r"\b(?:NPRR|NOGRR|PGRR|COPMGRR|RMGRR|RRGRR|SCR|PRR)\s*\d+", re.I),
     "names a specific revision request"),
    (re.compile(r"\b(?:SB|HB)\s*\d+\b", re.I), "names a specific bill"),
    (re.compile(r"\b(?:19|20)\d{2}\b"), "contains a year"),
    (re.compile(r"\b(?:january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\b", re.I), "contains a month"),
    (re.compile(r"\b\d+(?:\.\d+)?\s*(?:MW|GW|MWh|GWh|kV|%)\b", re.I),
     "contains a numeric threshold"),
    (re.compile(r"\bbatch\s+(?:zero|alpha|one|two|\d+)\b", re.I), "names a specific study batch"),
    (re.compile(r"\bOrder\s+\d+\b", re.I), "names a specific regulatory order"),
]

_PAREN_ANY = re.compile(r"\s*\(([^()]+)\)")


def norm(s):
    """Normalized matching key. Must stay identical to gallery_db._norm."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+ ]", " ", (s or "").lower())).strip()


def keyword_id(term):
    """Stable 12-hex-char id derived from the term itself.

    Deterministic on purpose: the same term yields the same id on every machine
    with no database round-trip and no counter to keep, which is what lets rows
    in `gallery.keyword_id` survive a nightly rebuild. Editing a term mints a
    new id -- that is why a renamed concept records the old spelling under
    `replaces:` so the link migration can follow it."""
    return hashlib.sha1(re.sub(r"\s+", " ", term).strip().lower()
                        .encode("utf-8")).hexdigest()[:12]


def strip_parens(term):
    return _PAREN_ANY.sub("", term or "").strip()


def acronym_parts(acronym):
    """Split an acronym field into usable tokens.

    A bare number is not an acronym: the old vocabulary carried "Senate Bill 6
    (SB6, 2025)" with acronym "SB6, 2025", and splitting on the comma
    registered "2025" as a surface form, which tagged every chart mentioning
    the year."""
    out = []
    for tok in re.split(r"[/,]", acronym or ""):
        tok = tok.strip()
        if len(tok) >= 2 and not norm(tok).replace(" ", "").isdigit():
            out.append(tok)
    return out


def is_acronym(form):
    """An all-caps token like RRS, ECRS or RTORPA — not a word.

    Acronyms get a lower length floor than words: "RRS" is as distinctive as
    "Responsive Reserve", whereas a three-letter *word* almost never is. The
    protection against a short form matching the wrong thing is not its length
    but where it is allowed to match — a form found only in a series name never
    assigns a keyword (see rules.weak_fields)."""
    s = re.sub(r"[^A-Za-z0-9+]", "", str(form or ""))
    return bool(s) and s.upper() == s and not s.isdigit() and len(s) <= 8


def form_min_length(form, min_len, min_acronym_len=3):
    return min_acronym_len if is_acronym(form) else min_len


class Concept:
    """One vocabulary entry, with its matching forms resolved."""

    __slots__ = ("term", "acronym", "facet", "broader", "glossary_ref",
                 "extension_reason", "scope_note", "aliases", "replaces",
                 "trending", "status", "keyword_id", "raw")

    def __init__(self, d):
        self.raw = d
        self.term = re.sub(r"\s+", " ", (d.get("term") or "").strip())
        self.acronym = (d.get("acronym") or "").strip() or None
        self.facet = d.get("facet")
        self.broader = d.get("broader")
        self.glossary_ref = d.get("glossary_ref")
        self.extension_reason = d.get("extension_reason")
        self.scope_note = d.get("scope_note")
        self.aliases = [a for a in (d.get("aliases") or []) if str(a).strip()]
        self.replaces = [r for r in (d.get("replaces") or []) if str(r).strip()]
        self.trending = bool(d.get("trending"))
        self.status = (d.get("status") or "candidate").strip()
        self.keyword_id = keyword_id(self.term) if self.term else None

    def declared_forms(self):
        """Every string the author offered as a surface form, unfiltered."""
        forms = {self.term, strip_parens(self.term)}
        for m in _PAREN_ANY.finditer(self.term):
            forms.update(p.strip() for p in re.split(r"[/,]", m.group(1)) if p.strip())
        forms.update(acronym_parts(self.acronym))
        forms.update(str(a).strip() for a in self.aliases)
        return {f for f in forms if f}

    def match_forms(self, blocklist, min_len, min_acronym_len=3):
        """Normalized forms that may actually match text: long enough, and not
        a word so common it would match half the gallery."""
        out = set()
        for f in self.declared_forms():
            n = norm(f)
            if n and n not in blocklist and len(n) >= form_min_length(
                    f, min_len, min_acronym_len):
                out.add(n)
        return out

    def __repr__(self):
        return f"<Concept {self.term!r} {self.status}>"


class Vocabulary:
    """The parsed YAML, with lookup tables built once."""

    def __init__(self, data, path=VOCAB_YAML):
        self.path = path
        self.version = data.get("version")
        self.compiled = data.get("compiled")
        self.rules = data.get("rules") or {}
        self.facets = data.get("facets") or {}
        self.blocklist = {norm(b) for b in (data.get("blocklist") or [])}
        self.rejected = data.get("rejected") or []
        self.concepts = [Concept(c) for c in (data.get("concepts") or [])]

        self.min_alias_length = int(self.rules.get("min_alias_length", 4))
        self.min_acronym_length = int(self.rules.get("min_acronym_length", 3))
        self.qualifying_fields = tuple(self.rules.get("qualifying_fields")
                                       or ("title", "sheet", "axis", "doc"))
        self.weak_fields = tuple(self.rules.get("weak_fields") or ("series",))
        self.max_keywords_per_chart = int(self.rules.get("max_keywords_per_chart", 6))

        self.by_id = {c.keyword_id: c for c in self.concepts}
        self.by_term = {norm(c.term): c for c in self.concepts}

    def matchable(self):
        """Concepts the extractor may assign — everything but retired ones."""
        return [c for c in self.concepts if c.status != "retired"]

    def form_index(self):
        """normalized surface form -> [concepts claiming it].

        A form claimed by two concepts is ambiguous; the validator rejects that,
        so at match time each list is expected to hold exactly one concept."""
        idx = {}
        for c in self.matchable():
            for f in c.match_forms(self.blocklist, self.min_alias_length,
                                   self.min_acronym_length):
                idx.setdefault(f, []).append(c)
        return idx

    def replaced_terms(self):
        """old normalized term -> concept that now covers it."""
        out = {}
        for c in self.concepts:
            for old in c.replaces:
                out.setdefault(norm(old), []).append(c)
        return out


def load(path=VOCAB_YAML):
    import yaml
    with open(path, encoding="utf-8") as f:
        return Vocabulary(yaml.safe_load(f), path)


def load_glossary(path=GLOSSARY_JSON):
    """-> {normalized surface form: canonical glossary term}.

    ERCOT's glossary carries 705 entries but far fewer concepts: 262 are
    acronym stubs whose whole definition is the expansion ("NON-SPIN" ->
    "Non-Spinning Reserve") and 30 are "See X" cross-references. Both are
    surface forms of a concept, not concepts, so they fold in here."""
    import json
    with open(path, encoding="utf-8") as f:
        terms = json.load(f)["terms"]
    out = {}
    for e in terms:
        t = re.sub(r"\s+", " ", (e.get("term_s") or "").strip())
        if not t:
            continue
        out.setdefault(norm(t), t)
        out.setdefault(norm(strip_parens(t)), t)
        for m in _PAREN_ANY.finditer(t):
            for part in re.split(r"[/,]", m.group(1)):
                if part.strip():
                    out.setdefault(norm(part), t)
    return out


def glossary_terms(path=GLOSSARY_JSON):
    """The exact `term_s` strings, for validating a glossary_ref citation."""
    import json
    with open(path, encoding="utf-8") as f:
        return {re.sub(r"\s+", " ", (e.get("term_s") or "").strip())
                for e in json.load(f)["terms"] if e.get("term_s")}
