-- ============================================================================
-- STATS.ILLUSTRATOR — relational storage for ERCOT EMIL report data (OPTIONAL)
-- ----------------------------------------------------------------------------
-- This is the "system of record" alternative to the JSON-snapshot folders under
-- Documents Database/STATS.ILLUSTRATOR/. Use it only if/when you need the FULL
-- historical archive with querying/aggregation (the folders hold just the latest
-- posting for the static homepage). ERCOT's API hands us the schema directly:
-- every report's /fields array lists each column's name + dataType, which maps
-- 1:1 to SQL below.
--
-- Note: the Power.Talks homepage is a static React SPA that fetches JSON files
-- over Apache — it CANNOT query MySQL directly. To feed the site from this DB,
-- add a nightly export that writes latest.json into the STATS.ILLUSTRATOR folder
-- (i.e. DB = record of truth, JSON files = the web-serving view).
--
-- MySQL/MariaDB (WAMP). Run once:  mysql -u root < stats_illustrator_schema.sql
-- ============================================================================

CREATE DATABASE IF NOT EXISTS stats_illustrator
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stats_illustrator;

-- --- Catalog: one row per EMIL product (mirrors emil_products_latest.json) ---
CREATE TABLE IF NOT EXISTS emil_product (
  emil_id                VARCHAR(32)  NOT NULL PRIMARY KEY,
  name                   VARCHAR(255) NOT NULL,
  report_type_id         INT          NULL,
  description            TEXT         NULL,
  status                 VARCHAR(32)  NULL,
  generation_frequency   VARCHAR(64)  NULL,
  channel                VARCHAR(64)  NULL,
  file_type              VARCHAR(64)  NULL,
  last_post_datetime     DATETIME     NULL,
  source_endpoint        VARCHAR(512) NULL,
  raw                    JSON         NULL,          -- full API record, verbatim
  retrieved_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_report_type (report_type_id)
) ENGINE=InnoDB;

-- ============================================================================
-- Example report: NP3-560-CD "Seven-Day Load Forecast by Forecast Zone"
-- Derived from the endpoint's /fields:
--   postedDatetime DATETIME, deliveryDate DATE, hourEnding VARCHAR,
--   north/south/west/houston/systemTotal DOUBLE, DSTFlag BOOLEAN
-- One table per report (columns are report-specific); name it np3_560_cd_*.
-- ============================================================================
CREATE TABLE IF NOT EXISTS np3_560_cd_7d_load_fcast_by_fzn (
  posted_datetime   DATETIME      NOT NULL,   -- when this forecast was published
  delivery_date     DATE          NOT NULL,   -- day being forecast
  hour_ending       VARCHAR(8)    NOT NULL,   -- e.g. "1:00" .. "24:00"
  dst_flag          TINYINT(1)    NOT NULL DEFAULT 0,
  north             DOUBLE        NULL,
  south             DOUBLE        NULL,
  west              DOUBLE        NULL,
  houston           DOUBLE        NULL,
  system_total      DOUBLE        NULL,
  loaded_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Natural key: a forecast value is unique per (posting, delivery hour, DST).
  -- Re-loading the same posting is a no-op via INSERT ... ON DUPLICATE KEY UPDATE.
  PRIMARY KEY (posted_datetime, delivery_date, hour_ending, dst_flag),
  KEY idx_delivery (delivery_date, hour_ending)
) ENGINE=InnoDB;

-- Example upsert (positional values map to the API's row arrays):
-- INSERT INTO np3_560_cd_7d_load_fcast_by_fzn
--   (posted_datetime, delivery_date, hour_ending, north, south, west, houston, system_total, dst_flag)
-- VALUES ('2026-08-20 00:30:00', '2026-08-27', '1:00', 23692.73, 18217.11, 10240.04, 16041.89, 68191.78, 0)
-- ON DUPLICATE KEY UPDATE
--   north=VALUES(north), south=VALUES(south), west=VALUES(west),
--   houston=VALUES(houston), system_total=VALUES(system_total), loaded_at=CURRENT_TIMESTAMP;
