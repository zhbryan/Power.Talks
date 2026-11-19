#!/usr/bin/env python3
"""gallery_db.py - the `gallery` schema side of the GALLERY chart routine.

Owns three things so that `gallery_charts_extractions_generations.py` stays
readable:

  1. the DDL for the two tables the routine maintains,
  2. the authoritative keyword vocabulary, and
  3. the invariant that ties them together.

Tables (schema `gallery`, local MySQL)
--------------------------------------
`gallery_charts`   one row per extracted chart PNG:
    chart_id         GC_<YYYYMMDD_HHMMSS>_<sequence>   (= the PNG file stem)
    chart_title      slide/page title or the chart's own title
    doc_name         source file name
    doc_type         'pdf'
    doc_group        committee short name from the source path
    doc_time         meeting date from the source path
    page_num         PDF page number
    sequence_id      order of the chart within its document (1-based)
    keywords         JSON array -- constrained, see the invariant below
    record_timestamp when the row was generated

`gallery_keywords` one row per (keyword, chart) pair:
    keyword_id       FK -> gallery.keyword_id.keyword_id
    keyword          FK -> gallery.keyword_id.term
    chart_id         FK -> gallery_charts.chart_id
    record_timestamp when the link was generated

The invariant
-------------
`gallery_charts.keywords` may only contain values that exist as
`gallery_keywords.keyword` for that same chart. The routine never writes the
two independently: `write_chart()` takes one keyword list, resolves it against
the vocabulary, writes `gallery_keywords` from the resolved set, and then
serialises *that same resolved set* into `gallery_charts.keywords`. Anything
the matcher could not resolve is dropped, not invented. `verify_invariant()`
re-checks the whole table afterwards and repairs any drift, so the guarantee
survives manual edits too.

The vocabulary itself is `gallery.keyword_id` (maintained by
`Database Codes/sync_keyword_ids.py` from the curated
`reference_info/ercot_keyword_vocabulary.yaml`). This module never invents terms.

Connection settings come from `Database Codes/ercot_api/db_config.json`, the
project's single source of truth for local MySQL, with the database forced to
the `gallery` entry of its "databases" list -- the same contract
`sync_keyword_ids.py` uses.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.dirname(HERE)                       # Database Codes/
PROJECT_ROOT = os.path.dirname(DB_DIR)
DB_CONFIG = os.path.join(DB_DIR, "ercot_api", "db_config.json")
KEYWORDS_JSON = os.path.join(DB_DIR, "reference_info", "ercot_market_keywords.json")

SCHEMA = "gallery"
VOCAB_TABLE = "keyword_id"       # maintained by sync_keyword_ids.py
CHARTS_TABLE = "gallery_charts"
LINKS_TABLE = "gallery_keywords"

# `keywords` is TEXT holding a JSON array rather than a native JSON column:
# the routine has to run against whatever MySQL/MariaDB build WAMP ships, and
# JSON column support differs across those. Read it with json.loads().
DDL_CHARTS = f"""
CREATE TABLE IF NOT EXISTS `{CHARTS_TABLE}` (
  `chart_id`         VARCHAR(64)  NOT NULL,
  `chart_title`      VARCHAR(512)     NULL,
  `doc_name`         VARCHAR(512) NOT NULL,
  `doc_type`         VARCHAR(16)  NOT NULL,
  `doc_group`        VARCHAR(64)      NULL,
  `doc_time`         DATE             NULL,
  `page_num`         VARCHAR(128)     NULL,
  `sequence_id`      INT          NOT NULL,
  `keywords`         TEXT             NULL
      COMMENT 'JSON array; every value must exist in gallery_keywords.keyword',
  `record_timestamp` DATETIME     NOT NULL,
  PRIMARY KEY (`chart_id`),
  KEY `ix_doc` (`doc_name`(191)),
  KEY `ix_group_time` (`doc_group`, `doc_time`),
  KEY `ix_doc_seq` (`doc_name`(191), `sequence_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Charts extracted to Documents Database/GALLERY by gallery_charts_extractions_generations.py'
"""

DDL_LINKS = f"""
CREATE TABLE IF NOT EXISTS `{LINKS_TABLE}` (
  `keyword_id`       CHAR(12)     NOT NULL,
  `keyword`          VARCHAR(255) NOT NULL,
  `chart_id`         VARCHAR(64)  NOT NULL,
  `record_timestamp` DATETIME     NOT NULL,
  PRIMARY KEY (`keyword_id`, `chart_id`),
  KEY `ix_chart` (`chart_id`),
  KEY `ix_keyword` (`keyword`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='keyword <-> chart links; keyword_id/keyword come from gallery.keyword_id'
"""

UPSERT_CHART = f"""
INSERT INTO `{CHARTS_TABLE}`
  (chart_id, chart_title, doc_name, doc_type, doc_group, doc_time,
   page_num, sequence_id, keywords, record_timestamp)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
  chart_title = VALUES(chart_title),
  doc_name    = VALUES(doc_name),
  doc_type    = VALUES(doc_type),
  doc_group   = VALUES(doc_group),
  doc_time    = VALUES(doc_time),
  page_num    = VALUES(page_num),
  sequence_id = VALUES(sequence_id),
  keywords    = VALUES(keywords)
"""

UPSERT_LINK = f"""
INSERT INTO `{LINKS_TABLE}`
  (keyword_id, keyword, chart_id, record_timestamp, source, matched_in)
VALUES (%s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE keyword = VALUES(keyword),
  source = VALUES(source), matched_in = VALUES(matched_in)
"""


# ─── connection ──────────────────────────────────────────────────────────────
def db_config():
    """Local MySQL settings with the database forced to the gallery schema."""
    with open(DB_CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    known = cfg.get("databases") or [cfg.get("database")]
    if SCHEMA not in known:
        raise SystemExit(f"'{SCHEMA}' is not listed in db_config.json databases: {known}")
    cfg["database"] = SCHEMA
    cfg["port"] = int(cfg.get("port", 3306))
    return cfg


def connect():
    import pymysql
    cfg = db_config()
    return pymysql.connect(
        host=cfg["host"], port=cfg["port"], user=cfg["user"],
        password=cfg["password"], database=cfg["database"],
        charset=cfg.get("charset", "utf8mb4"), autocommit=False,
    )


def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute(DDL_CHARTS)
        cur.execute(DDL_LINKS)
    conn.commit()


# ─── keyword vocabulary ──────────────────────────────────────────────────────
def _norm(s):
    """Match key: lowercase, punctuation to spaces, collapsed.

    Same shape as build_gallery_index.py's normalizer so a term resolves the
    same way here and on the web Gallery page."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+ ]", " ", (s or "").lower())).strip()


_PARENS = re.compile(r"\s*\([^()]*\)\s*$")


class Vocabulary:
    """The authoritative keyword list: `gallery.keyword_id`.

    `by_key` maps a normalized surface form -> (keyword_id, canonical term).
    Several surface forms point at one term: the term itself, the term without
    a trailing parenthetical, and each acronym. Resolution is exact-on-
    normalized-form only -- no fuzzy matching, because a wrong keyword is
    worse for search than a missing one."""

    def __init__(self, rows):
        self.terms = {}      # keyword_id -> term
        self.by_key = {}
        for kid, term, acronym in rows:
            term = re.sub(r"\s+", " ", (term or "").strip())
            if not kid or not term:
                continue
            self.terms[kid] = term
            for form in (term, _PARENS.sub("", term)):
                self.by_key.setdefault(_norm(form), (kid, term))
            m = re.search(r"\(([^()]+)\)\s*$", term)
            if m:
                self.by_key.setdefault(_norm(m.group(1)), (kid, term))
            for tok in re.split(r"[/,]", acronym or ""):
                tok = tok.strip()
                # A bare number in the acronym field is not an acronym. The
                # vocabulary carries "Senate Bill 6 (SB6, 2025)" with acronym
                # "SB6, 2025", and splitting that on the comma registered
                # "2025" as a surface form -- which tagged every chart that so
                # much as mentioned the year. One year alias cost 95 wrong
                # keyword links in one sweep.
                if len(tok) >= 2 and not _norm(tok).replace(" ", "").isdigit():
                    self.by_key.setdefault(_norm(tok), (kid, term))
        # longest-first, so "energy storage resource" wins over "storage"
        self._scan = sorted(self.by_key.items(), key=lambda kv: -len(kv[0]))

    def __len__(self):
        return len(self.terms)

    def resolve(self, keyword):
        """One keyword string -> (keyword_id, canonical term), or None."""
        cands = [keyword, _PARENS.sub("", keyword or "")]
        m = re.search(r"\(([^()]+)\)", keyword or "")
        if m:
            cands.append(m.group(1))
        for c in cands:
            hit = self.by_key.get(_norm(c))
            if hit:
                return hit
        return None

    def resolve_all(self, keywords):
        """Resolve a list, de-duplicated by keyword_id, order preserved.

        -> (resolved, dropped) where resolved is [(keyword_id, term)] and
        dropped is the input strings that are not in the vocabulary."""
        out, seen, dropped = [], set(), []
        for kw in keywords or []:
            hit = self.resolve(kw)
            if not hit:
                dropped.append(kw)
            elif hit[0] not in seen:
                seen.add(hit[0])
                out.append(hit)
        return out, dropped

    def scan_text(self, text, limit=12):
        """Keywords whose surface form literally occurs in `text`.

        The no-AI fallback, and a safety net under the AI's suggestions. Word-
        boundary matching on the normalized text; longest form first so a
        specific term is preferred over a generic one it contains."""
        hay = " " + _norm(text) + " "
        out, seen = [], set()
        for key, (kid, term) in self._scan:
            if kid in seen or len(key) < 3:
                continue
            if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", hay):
                seen.add(kid)
                out.append((kid, term))
                if len(out) >= limit:
                    break
        return out


def load_vocabulary(conn=None):
    """Read `gallery.keyword_id`; fall back to the curated JSON if that table
    is not reachable (so a dry run works without MySQL running)."""
    if conn is not None:
        with conn.cursor() as cur:
            # A retired term keeps its row so its id stays reserved, but it
            # must never tag a chart again.
            cur.execute(f"SELECT keyword_id, term, acronym FROM `{VOCAB_TABLE}` "
                        f"WHERE status <> 'retired'")
            rows = cur.fetchall()
        if rows:
            return Vocabulary(rows)
    with open(KEYWORDS_JSON, encoding="utf-8") as f:
        kws = json.load(f)["keywords"]
    return Vocabulary([(k.get("keyword_id"), k.get("term"), k.get("acronym"))
                       for k in kws if k.get("status") != "retired"])


# ─── writes ──────────────────────────────────────────────────────────────────
def write_chart(conn, chart, resolved, stamp, source="scan",
                scan_fields=None, matched_in=None):
    """Upsert one chart plus its keyword links in a single transaction.

    `resolved` is [(keyword_id, term)] -- which is what makes the invariant
    hold by construction: the JSON array stored on the chart row is serialised
    from the very same list that produced the `gallery_keywords` rows.

    `source` says how these keywords were decided ("scan" for a literal
    vocabulary match, "ai" for a model reading the page). Only links of the
    same source are pruned, so a literal re-scan cannot delete what the model
    concluded from the page text, and vice versa.

    `scan_fields` is the text the chart was matched on, by field; it is stored
    on the chart so `retag_charts.py` can re-apply a changed vocabulary to the
    whole gallery without reopening the source file."""
    terms = [t for _, t in resolved]
    matched_in = matched_in or {}
    with conn.cursor() as cur:
        cur.execute(UPSERT_CHART, (
            chart["chart_id"], chart.get("chart_title"), chart["doc_name"],
            chart["doc_type"], chart.get("doc_group"), chart.get("doc_time"),
            str(chart.get("page_num")) if chart.get("page_num") is not None else None,
            int(chart["sequence_id"]),
            json.dumps(terms, ensure_ascii=False), stamp,
        ))
        if scan_fields:
            cur.execute(f"UPDATE `{CHARTS_TABLE}` SET scan_text=%s WHERE chart_id=%s",
                        (json.dumps({k: v for k, v in scan_fields.items() if v},
                                    ensure_ascii=False), chart["chart_id"]))
        if resolved:
            cur.executemany(UPSERT_LINK,
                            [(kid, term, chart["chart_id"], stamp, source,
                              matched_in.get(kid))
                             for kid, term in resolved])
            ids = [kid for kid, _ in resolved]
            ph = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM `{LINKS_TABLE}` WHERE chart_id=%s "
                        f"AND source=%s AND keyword_id NOT IN ({ph})",
                        [chart["chart_id"], source] + ids)
        else:
            cur.execute(f"DELETE FROM `{LINKS_TABLE}` WHERE chart_id=%s AND source=%s",
                        (chart["chart_id"], source))
    conn.commit()


def retire_charts(conn, chart_ids):
    """Delete chart rows and their keyword links for a previous extraction.

    Called before a document is re-extracted. `chart_id` carries the timestamp
    of the pass that produced it, so a re-extraction mints *new* ids and cannot
    overwrite the old rows by upsert -- without this the same chart accumulates
    one row per pass, and the PNG it points at is orphaned. Retiring the prior
    ids first makes a re-run idempotent, which is what lets a backfill night be
    repeated safely."""
    ids = [c for c in chart_ids if c]
    if not ids:
        return 0
    ph = ",".join(["%s"] * len(ids))
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM `{LINKS_TABLE}` WHERE chart_id IN ({ph})", ids)
        cur.execute(f"DELETE FROM `{CHARTS_TABLE}` WHERE chart_id IN ({ph})", ids)
        n = cur.rowcount
    conn.commit()
    return n


def known_charts(conn):
    """-> {doc_name: {chart_id, ...}} for the incremental skip check."""
    out = {}
    with conn.cursor() as cur:
        cur.execute(f"SELECT doc_name, chart_id FROM `{CHARTS_TABLE}`")
        for doc_name, chart_id in cur.fetchall():
            out.setdefault(doc_name, set()).add(chart_id)
    return out


def verify_invariant(conn, repair=True):
    """Re-assert requirement 3: every value in `gallery_charts.keywords` must
    exist as a `gallery_keywords.keyword` row for that chart.

    Reads both tables, rewrites any chart whose JSON array disagrees with its
    links (dropping unbacked values, adding backed ones that are missing), and
    deletes links that point at no chart. Returns a report dict; with
    `repair=False` it only reports, which is what `--verify-only` uses."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT chart_id, keywords FROM `{CHARTS_TABLE}`")
        charts = cur.fetchall()
        cur.execute(f"SELECT chart_id, keyword FROM `{LINKS_TABLE}`")
        links = {}
        for cid, kw in cur.fetchall():
            links.setdefault(cid, []).append(kw)
        cur.execute(f"SELECT l.chart_id FROM `{LINKS_TABLE}` l "
                    f"LEFT JOIN `{CHARTS_TABLE}` c ON c.chart_id=l.chart_id "
                    f"WHERE c.chart_id IS NULL")
        orphan_link_charts = sorted({r[0] for r in cur.fetchall()})

    fixed, offenders = [], []
    for cid, raw in charts:
        try:
            listed = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            listed = []
        backed = links.get(cid, [])
        # Keep the chart's own order, but only values the links table backs,
        # then append any backed keyword the array had lost.
        allowed = [k for k in listed if k in backed]
        allowed += [k for k in backed if k not in allowed]
        if allowed != listed:
            offenders.append((cid, [k for k in listed if k not in backed],
                              [k for k in backed if k not in listed]))
            if repair:
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE `{CHARTS_TABLE}` SET keywords=%s "
                                f"WHERE chart_id=%s",
                                (json.dumps(allowed, ensure_ascii=False), cid))
                fixed.append(cid)
    if repair and orphan_link_charts:
        ph = ",".join(["%s"] * len(orphan_link_charts))
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM `{LINKS_TABLE}` WHERE chart_id IN ({ph})",
                        orphan_link_charts)
    if repair:
        conn.commit()
    return {"charts": len(charts), "offenders": offenders, "repaired": fixed,
            "orphan_links": orphan_link_charts}


# ─── schema migration ────────────────────────────────────────────────────────
# Columns added 2026-11-19 with the controlled vocabulary. `ensure_columns()`
# adds them in place, so an existing gallery upgrades without a reload.
ADDED_COLUMNS = [
    (CHARTS_TABLE, "scan_text", f"""
        ALTER TABLE `{CHARTS_TABLE}` ADD COLUMN `scan_text` MEDIUMTEXT NULL
        COMMENT 'JSON object of the text this chart was matched on, by field:
                 title / sheet / axis / doc / series. Stored so the corpus can
                 be re-tagged after a vocabulary change without re-opening the
                 source workbook through Excel COM.'
    """),
    (LINKS_TABLE, "source", f"""
        ALTER TABLE `{LINKS_TABLE}` ADD COLUMN `source` VARCHAR(8) NOT NULL DEFAULT 'scan'
        COMMENT 'scan = literal vocabulary match, ai = model-assigned, manual = hand-set.
                 retag_charts.py rebuilds scan rows only.'
    """),
    (LINKS_TABLE, "matched_in", f"""
        ALTER TABLE `{LINKS_TABLE}` ADD COLUMN `matched_in` VARCHAR(64) NULL
        COMMENT 'Which chart fields the surface form was found in, comma
                 separated, so a wrong keyword can be traced to its evidence.'
    """),
]


def ensure_columns(conn, log=None):
    """Add any missing column from ADDED_COLUMNS. Safe to call every run."""
    added = []
    with conn.cursor() as cur:
        for table, column, ddl in ADDED_COLUMNS:
            cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                              AND column_name = %s""", (SCHEMA, table, column))
            if cur.fetchone()[0] == 0:
                cur.execute(" ".join(ddl.split()))
                added.append(f"{table}.{column}")
    conn.commit()
    if added and log:
        log(f"schema: added {', '.join(added)}")
    return added


# ─── concept matching ────────────────────────────────────────────────────────
# Where a surface form is found decides whether it may assign a keyword:
#   title  the chart's own caption -- the strongest statement of its subject
#   doc    the source document's file name, a label someone chose on purpose
#   page   the text of the PDF page the chart sits on -- real evidence, but
#          prose mentions things in passing, so it ranks below the two labels
#   series a single plotted series (kept for audit, never assigns)
# Order matters: it decides which keywords survive max_keywords_per_chart.
# The distinction is not academic. While workbooks were still a source, a
# series called "COP HSL" on the monthly wind-forecast charts put "Current
# Operating Plan (COP)" on 522 charts -- a third of the gallery -- none of
# which was about the COP. Workbooks are gone, but the rule stays: a term a
# chart merely mentions is not what the chart is about.
FIELD_PRIORITY = ("title", "doc", "page", "series")


class ConceptVocabulary:
    """The controlled vocabulary, matched field by field.

    Built from `ercot_market_keywords.json`, which build_keywords_json.py
    generates from the curated YAML and validate_vocabulary.py guarantees is
    unambiguous -- every surface form belongs to exactly one concept."""

    def __init__(self, data):
        rules = data.get("rules") or {}
        self.qualifying = tuple(rules.get("qualifying_fields") or ("title", "sheet", "axis", "doc"))
        self.weak = tuple(rules.get("weak_fields") or ("series",))
        self.max_keywords = int(rules.get("max_keywords_per_chart", 6))
        self.concepts = {}
        forms = []
        for k in data.get("keywords", []):
            if k.get("status") == "retired":
                continue
            kid, term = k.get("keyword_id"), k.get("term")
            if not kid or not term:
                continue
            self.concepts[kid] = {"term": term, "status": k.get("status"),
                                  "facet": k.get("facet")}
            for f in k.get("match_forms") or []:
                forms.append((f, kid))
        # longest form first: "non-spinning reserve" must win over "reserve"
        self._scan = sorted(forms, key=lambda kv: -len(kv[0]))
        self._re = {f: re.compile(r"(?<![a-z0-9])" + re.escape(f) + r"(?![a-z0-9])")
                    for f, _ in forms}

    def __len__(self):
        return len(self.concepts)

    def match(self, fields):
        """fields: {field name: text} -> [(keyword_id, term, matched_in)].

        A concept is assigned only when one of its forms appears in a
        qualifying field. A hit in a weak field alone is recorded nowhere --
        it is evidence that the chart mentions the term, not that it is about
        it."""
        hay = {}
        for name in FIELD_PRIORITY:
            txt = fields.get(name)
            if txt:
                hay[name] = " " + _norm(txt) + " "
        found = {}
        for form, kid in self._scan:
            if kid in found:
                continue
            rx = self._re[form]
            where = [n for n in FIELD_PRIORITY if n in hay and rx.search(hay[n])]
            if not where:
                continue
            if not any(n in self.qualifying for n in where):
                continue                      # weak-field-only: not aboutness
            found[kid] = (len(form), where)
        ranked = sorted(found.items(),
                        key=lambda kv: (FIELD_PRIORITY.index(kv[1][1][0]), -kv[1][0]))
        out = []
        for kid, (_, where) in ranked[:self.max_keywords]:
            out.append((kid, self.concepts[kid]["term"], ",".join(where)))
        return out


def load_concepts(path=KEYWORDS_JSON):
    with open(path, encoding="utf-8") as f:
        return ConceptVocabulary(json.load(f))


def chart_fields(row, scan_text):
    """Assemble the matchable text for one chart.

    The columns already hold the title and the document name, so re-tagging
    works on every chart whether or not its stored scan_text has been filled in
    yet; scan_text adds the page text the chart was found on."""
    fields = {"title": row.get("chart_title") or "",
              "doc": row.get("doc_name") or ""}
    if scan_text:
        try:
            extra = json.loads(scan_text)
        except Exception:
            extra = None
        if isinstance(extra, dict):
            for k, v in extra.items():
                if not v:
                    continue
                fields[k] = (fields.get(k, "") + " " + str(v)).strip()
    return fields


def write_scan_text(conn, chart_id, fields):
    """Persist the text a chart was matched on, as a JSON object by field."""
    payload = json.dumps({k: v for k, v in (fields or {}).items() if v},
                         ensure_ascii=False)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE `{CHARTS_TABLE}` SET scan_text = %s WHERE chart_id = %s",
                    (payload, chart_id))
    return payload
