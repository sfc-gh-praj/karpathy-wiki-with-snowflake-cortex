-- Creates all infrastructure needed for the manufacturing wiki
-- Run this first before uploading any PDFs

-- 1. Database and schema
CREATE DATABASE IF NOT EXISTS MANUFACTURING_WIKI;
CREATE SCHEMA IF NOT EXISTS MANUFACTURING_WIKI.KNOWLEDGE;

USE DATABASE MANUFACTURING_WIKI;
USE SCHEMA KNOWLEDGE;

-- 2. Internal stage with directory enabled
CREATE STAGE IF NOT EXISTS MFG_STAGE
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE')
  COMMENT = 'Manufacturing PDF documents stage';

-- 3. RAW_DOCUMENTS — stores AI_PARSE_DOCUMENT output per PDF
CREATE TABLE IF NOT EXISTS RAW_DOCUMENTS (
  DOC_ID         VARCHAR(200) NOT NULL,     -- derived from filename, unique key
  FILE_NAME      VARCHAR(500),
  STAGE_PATH     VARCHAR(1000),
  PARSED_TEXT    VARIANT,                   -- full AI_PARSE_DOCUMENT JSON output
  PLAIN_TEXT     TEXT,                      -- flat extracted text for COMPLETE calls
  PAGE_COUNT     INT,
  DOC_TYPE       VARCHAR(100),              -- equipment_spec|maintenance|qc|sds|production|catalog|fmea
  INGESTED_AT    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_raw_documents PRIMARY KEY (DOC_ID)
);

-- 4. WIKI_PAGES — LLM-compiled wiki (one row per entity/topic/concept)
CREATE TABLE IF NOT EXISTS WIKI_PAGES (
  PAGE_ID        VARCHAR(200) NOT NULL,     -- slug: 'equipment-M042-specs'
  PAGE_TITLE     VARCHAR(500),
  CATEGORY       VARCHAR(100),              -- equipment|maintenance|qc|safety|production|supplier|fmea|synthesis
  CONTENT_MD     TEXT,                      -- full markdown body
  SOURCE_DOCS    ARRAY,                     -- list of contributing DOC_IDs
  VERSION        INT DEFAULT 1,
  CREATED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  UPDATED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_wiki_pages PRIMARY KEY (PAGE_ID)
);

-- 5. WIKI_INDEX — compact catalog of all wiki pages (used for query routing)
CREATE TABLE IF NOT EXISTS WIKI_INDEX (
  PAGE_ID            VARCHAR(200) NOT NULL,
  PAGE_TITLE         VARCHAR(500),
  CATEGORY           VARCHAR(100),
  ONE_LINE_SUMMARY   VARCHAR(1000),         -- LLM-generated one-liner
  KEYWORDS           ARRAY,                 -- LLM-extracted keywords
  SOURCE_DOC_COUNT   INT DEFAULT 1,
  UPDATED_AT         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_wiki_index PRIMARY KEY (PAGE_ID)
);

-- 6. INGESTION_LOG — append-only audit trail
CREATE TABLE IF NOT EXISTS INGESTION_LOG (
  LOG_ID         VARCHAR(36) DEFAULT UUID_STRING(),
  OPERATION      VARCHAR(50),               -- ingest|wiki_compile|query|lint|wiki_update
  DOC_ID         VARCHAR(200),
  PAGE_ID        VARCHAR(200),
  DETAIL         TEXT,
  STATUS         VARCHAR(20) DEFAULT 'success',  -- success|error|skipped
  DURATION_MS    INT,
  PERFORMED_AT   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 7. WIKI_SAVED_ANSWERS — answers filed back into wiki (compounding)
CREATE TABLE IF NOT EXISTS WIKI_SAVED_ANSWERS (
  ANSWER_ID      VARCHAR(36) DEFAULT UUID_STRING(),
  QUESTION       TEXT,
  ANSWER_MD      TEXT,
  WIKI_PAGE_ID   VARCHAR(200),              -- if saved as wiki page
  CITATIONS      ARRAY,
  LANE_USED      VARCHAR(20),               -- point_lookup|synthesis
  CREATED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 8. PROMPT_REGISTRY — versioned prompt storage, decoupled from SP code
--    Only one row per PROMPT_NAME should have IS_ACTIVE = TRUE.
--    COMPILE_WIKI_PAGE reads the active prompt at runtime instead of
--    using a hardcoded constant, so prompts can be updated without
--    redeploying the stored procedure.
CREATE TABLE IF NOT EXISTS PROMPT_REGISTRY (
  PROMPT_ID      VARCHAR(36) DEFAULT UUID_STRING(),
  PROMPT_NAME    VARCHAR(100) NOT NULL,     -- logical name: 'wiki_compiler'
  VERSION        INT NOT NULL,             -- monotonically increasing: 1, 2, 3...
  PROMPT_TEXT    TEXT NOT NULL,
  IS_ACTIVE      BOOLEAN DEFAULT FALSE,    -- TRUE = this version is used by the SP
  NOTES          TEXT,
  CREATED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_prompt_registry PRIMARY KEY (PROMPT_ID),
  CONSTRAINT uq_prompt_name_version UNIQUE (PROMPT_NAME, VERSION)
);

-- Add PROMPT_ID to WIKI_PAGES so every compiled page records which
-- prompt version produced it (NULL = compiled before registry existed)
ALTER TABLE WIKI_PAGES ADD COLUMN IF NOT EXISTS PROMPT_ID VARCHAR(36);

-- Add temporal period columns to RAW_DOCUMENTS (populated during ingestion)
-- PERIOD_LABEL examples: "Q3 2025", "Week of 2025-07-01", "2026-02"
ALTER TABLE RAW_DOCUMENTS ADD COLUMN IF NOT EXISTS PERIOD_START DATE;
ALTER TABLE RAW_DOCUMENTS ADD COLUMN IF NOT EXISTS PERIOD_END   DATE;
ALTER TABLE RAW_DOCUMENTS ADD COLUMN IF NOT EXISTS PERIOD_LABEL VARCHAR(50);

-- Add period label to WIKI_PAGES (inherited from source document at compile time)
ALTER TABLE WIKI_PAGES ADD COLUMN IF NOT EXISTS PERIOD_LABEL VARCHAR(50);

-- ============================================================
-- Cortex Search Service — WIKI_SEARCH
-- Rebuilding with PERIOD_LABEL as an attribute column enables
-- server-side period filtering in ANSWER_QUESTION queries.
-- ============================================================
CREATE OR REPLACE CORTEX SEARCH SERVICE WIKI_SEARCH
  ON CONTENT_MD
  ATTRIBUTES PAGE_ID, CATEGORY, PERIOD_LABEL
  WAREHOUSE = QUICKSTART
  TARGET_LAG = '1 hour'
AS (
  SELECT p.PAGE_ID, p.PAGE_TITLE, p.CATEGORY, p.CONTENT_MD,
         i.ONE_LINE_SUMMARY, p.PERIOD_LABEL
  FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES p
  JOIN MANUFACTURING_WIKI.KNOWLEDGE.WIKI_INDEX i USING (PAGE_ID)
);
GRANT USAGE ON DATABASE MANUFACTURING_WIKI TO ROLE SYSADMIN;
GRANT USAGE ON SCHEMA MANUFACTURING_WIKI.KNOWLEDGE TO ROLE SYSADMIN;
GRANT ALL ON ALL TABLES IN SCHEMA MANUFACTURING_WIKI.KNOWLEDGE TO ROLE SYSADMIN;
GRANT ALL ON STAGE MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE TO ROLE SYSADMIN;
