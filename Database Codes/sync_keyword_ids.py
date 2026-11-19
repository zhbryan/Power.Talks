#!/usr/bin/env python3
"""sync_keyword_ids.py - load the ERCOT market keyword list into MySQL.

Reads `Database Codes/reference_info/ercot_market_keywords.json` (rebuilt from
the curated .md by build_keywords_json.py) and upserts it into the table
`keyword_id` in the local `gallery` schema:

    keyword_id    CHAR(12)      PK - stable digest of the normalized term
    term          VARCHAR(255)  UNIQUE
    acronym       VARCHAR(64)
    category      VARCHAR(128)
    description   TEXT
    trending      TINYINT(1)
    generated_at  DATETIME      when this id was first created - never rewritten
    updated_at    DATETIME      last time the row's content changed

Connection settings come from `Database Codes/ercot_api/db_config.json`, the
single source of truth for local MySQL access, with the database forced to the
`gallery` entry of its "databases" list.

`generated_at` is preserved across runs: re-running after a keyword list rebuild
updates the text of changed rows and inserts new ones, but an existing id keeps
its original creation timestamp. Terms dropped from the .md are reported, not
deleted -- removal is a manual call, since other tables may reference the id.

    py -3 "Database Codes/sync_keyword_ids.py"
    py -3 "Database Codes/sync_keyword_ids.py" --quiet
    py -3 "Database Codes/sync_keyword_ids.py" --dry-run
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
KEYWORDS_JSON = os.path.join(HERE, "reference_info", "ercot_market_keywords.json")
DB_CONFIG = os.path.join(HERE, "ercot_api", "db_config.json")
TABLE = "keyword_id"
SCHEMA = "gallery"

DDL = f"""
CREATE TABLE IF NOT EXISTS `{TABLE}` (
  `keyword_id`   CHAR(12)     NOT NULL,
  `term`         VARCHAR(255) NOT NULL,
  `acronym`      VARCHAR(64)      NULL,
  `category`     VARCHAR(128)     NULL,
  `description`  TEXT             NULL,
  `trending`     TINYINT(1)   NOT NULL DEFAULT 0,
  `facet`        VARCHAR(64)      NULL,
  `broader`      VARCHAR(255)     NULL
      COMMENT 'The parent concept, where one was declared. Hierarchy, not overlap.',
  `glossary_ref` VARCHAR(255)     NULL
      COMMENT 'Exact term_s in ERCOT''s own glossary; NULL means a declared extension.',
  `status`       VARCHAR(12)  NOT NULL DEFAULT 'active'
      COMMENT 'active = offered in the Gallery picker; candidate = matchable but hidden until it has a chart.',
  `generated_at` DATETIME     NOT NULL,
  `updated_at`   DATETIME     NOT NULL,
  PRIMARY KEY (`keyword_id`),
  UNIQUE KEY `uq_term` (`term`),
  KEY `ix_category` (`category`),
  KEY `ix_trending` (`trending`),
  KEY `ix_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='ERCOT keyword concepts; source: Database Codes/reference_info/ercot_keyword_vocabulary.yaml'
"""

UPSERT = f"""
INSERT INTO `{TABLE}`
  (keyword_id, term, acronym, category, description, trending,
   facet, broader, glossary_ref, status, generated_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
ON DUPLICATE KEY UPDATE
  -- updated_at MUST come first: MySQL evaluates these assignments in order, so
  -- any column listed above it would already hold its NEW value here and the
  -- comparison would always say "unchanged".
  updated_at  = IF(term <=> VALUES(term)
                   AND acronym <=> VALUES(acronym)
                   AND category <=> VALUES(category)
                   AND description <=> VALUES(description)
                   AND trending <=> VALUES(trending)
                   AND facet <=> VALUES(facet)
                   AND broader <=> VALUES(broader)
                   AND glossary_ref <=> VALUES(glossary_ref)
                   AND status <=> VALUES(status),
                   updated_at, NOW()),
  term        = VALUES(term),
  acronym     = VALUES(acronym),
  category    = VALUES(category),
  description = VALUES(description),
  trending    = VALUES(trending),
  facet        = VALUES(facet),
  broader      = VALUES(broader),
  glossary_ref = VALUES(glossary_ref),
  status       = VALUES(status)
"""

# Columns added 2026-11-19 with the controlled vocabulary; added in place so an
# existing gallery upgrades without a reload.
ADD_COLUMNS = [
    ("facet",        f"ALTER TABLE `{TABLE}` ADD COLUMN `facet` VARCHAR(64) NULL"),
    ("broader",      f"ALTER TABLE `{TABLE}` ADD COLUMN `broader` VARCHAR(255) NULL"),
    ("glossary_ref", f"ALTER TABLE `{TABLE}` ADD COLUMN `glossary_ref` VARCHAR(255) NULL"),
    ("status",       f"ALTER TABLE `{TABLE}` ADD COLUMN `status` VARCHAR(12) NOT NULL DEFAULT 'active'"),
]


def ensure_columns(conn, verbose=True):
    """Add any column missing from an older `keyword_id` table."""
    added = []
    with conn.cursor() as cur:
        for column, ddl in ADD_COLUMNS:
            cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                              AND column_name = %s""", (SCHEMA, TABLE, column))
            if cur.fetchone()[0] == 0:
                cur.execute(ddl)
                added.append(column)
    conn.commit()
    if added and verbose:
        print(f"  schema: added {', '.join(added)}")
    return added


def db_config():
    """Local MySQL settings, database forced to the gallery schema."""
    with open(DB_CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    known = cfg.get("databases") or [cfg.get("database")]
    if SCHEMA not in known:
        raise SystemExit(f"'{SCHEMA}' is not listed in db_config.json databases: {known}")
    cfg["database"] = SCHEMA
    cfg["port"] = int(cfg.get("port", 3306))
    return cfg


def load_keywords():
    with open(KEYWORDS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    rows, seen = [], {}
    for k in data["keywords"]:
        kid = k.get("keyword_id")
        if not kid:
            raise SystemExit("ercot_market_keywords.json has no keyword_id - "
                             "run build_keywords_json.py first.")
        if kid in seen:
            print(f"  duplicate term skipped: {k['term']!r} (same id as {seen[kid]!r})")
            continue
        seen[kid] = k["term"]
        rows.append((kid, k["term"], k.get("acronym"), k.get("category"),
                     k.get("description"), 1 if k.get("trending") else 0,
                     k.get("facet"), k.get("broader"), k.get("glossary_ref"),
                     k.get("status") or "active"))
    return data, rows


def main():
    quiet = "--quiet" in sys.argv
    dry = "--dry-run" in sys.argv

    data, rows = load_keywords()
    if dry:
        print(f"{len(rows)} keyword(s) would be synced to {SCHEMA}.{TABLE}")
        for r in rows[:5]:
            print("   ", r[0], "|", r[1])
        return 0

    import pymysql
    cfg = db_config()
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                           password=cfg["password"], database=cfg["database"],
                           charset=cfg.get("charset", "utf8mb4"), autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        ensure_columns(conn, verbose=not quiet)
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM `{TABLE}`")
            before = cur.fetchone()[0]
            cur.executemany(UPSERT, rows)
            cur.execute(f"SELECT COUNT(*) FROM `{TABLE}`")
            after = cur.fetchone()[0]
            ids = [r[0] for r in rows]
            ph = ",".join(["%s"] * len(ids))
            cur.execute(f"SELECT keyword_id, term FROM `{TABLE}` "
                        f"WHERE keyword_id NOT IN ({ph})", ids)
            retired = cur.fetchall()
            # A term dropped from the vocabulary is marked retired, never
            # deleted: its id stays reserved so it can never be minted again
            # for a different meaning, and anything still pointing at it keeps
            # resolving. The Gallery hides retired terms from the picker.
            if retired:
                cur.execute(f"UPDATE `{TABLE}` SET status = 'retired' "
                            f"WHERE keyword_id NOT IN ({ph}) AND status <> 'retired'", ids)
        conn.commit()
    finally:
        conn.close()

    inserted = after - before
    if quiet:
        line = (f"Keyword ids: {len(rows)} synced to {SCHEMA}.{TABLE} "
                f"({inserted} new, {after} total)")
        if retired:
            line += f" | {len(retired)} retired"
        print(line)
    else:
        print(f"Synced {len(rows)} keyword(s) -> {SCHEMA}.{TABLE}")
        print(f"  {inserted} inserted, {len(rows) - inserted} already present, {after} rows total.")
        if retired:
            print(f"  {len(retired)} row(s) no longer in the vocabulary (marked retired, not deleted):")
            for kid, term in retired[:10]:
                print(f"    {kid} | {term}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
