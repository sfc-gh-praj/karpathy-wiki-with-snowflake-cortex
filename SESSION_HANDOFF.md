# Session Handoff — Karpathy LLM-Wiki Manufacturing Demo

**Date of last session**: April 10, 2026  
**Working directory**: `/Users/praj/Documents/cortex-code-demos/karpathy-workflow`  
**Git**: Not a git repo.

---

## Snowflake Connection

| Key | Value |
|-----|-------|
| SQL Connection | `COCO_JK` |
| Agent Connection | `snowhouse` |
| Account | `SFSENORTHAMERICA-PRAJ01` |
| User | `spcs_user` |
| Warehouse | `QUICKSTART` |
| Role | `accountadmin` |
| Database | `MANUFACTURING_WIKI` |
| Schema | `KNOWLEDGE` |
| Active LLM | `claude-sonnet-4-5` |

**Rule**: Always use `snowhouse` for Agent Connection and `COCO_JK` for SQL Connection. Do NOT use `snow sql -f` for stored procedures that contain Python f-strings — use `snowflake_sql_execute` directly.

---

## Live Snowflake State (as of last session)

| Table | Rows | Notes |
|-------|------|-------|
| `RAW_DOCUMENTS` | 63 | 63 PDFs ingested from stage |
| `WIKI_PAGES` | 101 | **98 have `PROMPT_ID IS NULL`** (need recompile) |
| `WIKI_INDEX` | 101 | Mirrors WIKI_PAGES |
| `PROMPT_REGISTRY` | 1 | `wiki_compiler` v1, `IS_ACTIVE = TRUE` |
| `INGESTION_LOG` | — | |
| `WIKI_SAVED_ANSWERS` | — | |

**Stage**: `@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE` (63 PDFs)  
**Cortex Search Service**: `WIKI_SEARCH` (101 pages indexed)

### Active Prompt
```
PROMPT_ID:   2ce97e17-0dd5-4603-8bd3-d23aee829da0
PROMPT_NAME: wiki_compiler
VERSION:     1
IS_ACTIVE:   TRUE
NOTES:       Initial versioned prompt. Restores cross-reference instructions
             (→ See: page-id) that were stripped during hotfix sessions.
CREATED_AT:  2026-04-09 11:41:48
```

---

## What This System Does (Karpathy-Pattern)

**Offline** (ingest): PDFs → `PARSE_DOCUMENT` → `COMPILE_WIKI_PAGE` SP → structured wiki pages stored in `WIKI_PAGES`  
**Online** (query): User question → `ANSWER_FROM_WIKI` SP → classifier routes to `point_lookup` or `synthesis` lane → Cortex Search → optional `COMPLETE` → answer

The key insight: the LLM answers from compiled wiki pages, not raw PDF chunks.

---

## File Structure

```
karpathy-workflow/
├── snowflake/
│   ├── 01_setup_infra.sql       ← DDL for all tables incl. PROMPT_REGISTRY
│   ├── 02_ingest_pipeline.sql   ← COMPILE_WIKI_PAGE SP (reads prompt from registry)
│   ├── 03_query_procedure.sql   ← ANSWER_FROM_WIKI SP (two-lane routing)
│   └── 04_lint_procedure.sql    ← LINT_WIKI_PAGE SP
├── pdf_generators/
│   ├── data_generator.py        ← Shared universe (seed=42): 200 machines, 10 lines, etc.
│   ├── generate_all.py          ← Entry point to generate all 63 PDFs
│   └── doc_types/
│       ├── equipment_spec.py
│       ├── parts_catalog.py
│       ├── fmea_worksheet.py
│       ├── maintenance_report.py
│       ├── qc_report.py
│       ├── production_log.py
│       └── safety_data_sheet.py
├── streamlit/
│   ├── app.py                   ← Streamlit UI
│   └── utils/wiki_ops.py
├── pdfs/                        ← 63 generated PDFs + 7 smoke test PDFs
├── output/
│   ├── architecture.png
│   └── karpathy_wiki_flow.gif
├── DOCUMENT_TYPES.md            ← Full reference for all 7 doc types
├── SESSION_HANDOFF.md           ← This file
├── FLOW_GUIDE.md
├── full_plan.md
├── implementation-plan.md
└── requirements.txt
```

---

## Manufacturing Universe (seed=42)

| Entity | Count | ID Format |
|--------|-------|-----------|
| Machines | 200 | M001–M200 |
| Production lines | 10 | L1–L10 |
| Suppliers | 20 | S001–S020 |
| Chemicals | 50 | CHM-0001–CHM-0050 |
| Technicians | 30 | T001–T030 |

**Products**: precision metal components, sub-assemblies, industrial fasteners, hydraulic manifolds, sensor housings — sold to automotive, aerospace, heavy equipment OEMs.

---

## 7 PDF Document Types

| # | Type | Scope | Key Content |
|---|------|-------|-------------|
| 1 | `equipment_spec` | 1 machine | Technical specs, PM schedule, installation reqs |
| 2 | `parts_catalog` | 3–5 machines | Spend analysis, master parts list with stock status |
| 3 | `fmea_worksheet` | 1 machine | RPN scoring (S×O×D), 12 subsystems, 48 failure modes |
| 4 | `maintenance_report` | 1 line, 1 quarter | PM KPIs, task log, downtime analysis |
| 5 | `qc_report` | 1 line, 1 quarter | Defect rate, SPC chart, Cpk per machine |
| 6 | `production_log` | 1 line, 1 week | Hourly output, OEE, downtime events, shift handover |
| 7 | `safety_data_sheet` | 1 chemical | All 16 GHS sections |

See `DOCUMENT_TYPES.md` for full section-by-section breakdown and cross-doc relationship map.

---

## PROMPT_REGISTRY Architecture

### Why it exists
The `wiki_compiler` prompt was previously hardcoded as a Python constant inside `COMPILE_WIKI_PAGE`. Problems:
- Could not change prompt rules without redeploying the SP
- Could not see which prompt version compiled an old page
- Different pages were compiled with different versions across hotfix sessions

### Schema (`01_setup_infra.sql`)
```sql
CREATE TABLE IF NOT EXISTS PROMPT_REGISTRY (
  PROMPT_ID      VARCHAR(36) DEFAULT UUID_STRING(),
  PROMPT_NAME    VARCHAR(100) NOT NULL,     -- logical name: 'wiki_compiler'
  VERSION        INT NOT NULL,              -- monotonically increasing
  PROMPT_TEXT    TEXT NOT NULL,
  IS_ACTIVE      BOOLEAN DEFAULT FALSE,     -- TRUE = this version is in use
  NOTES          TEXT,
  CREATED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  CONSTRAINT pk_prompt_registry PRIMARY KEY (PROMPT_ID),
  CONSTRAINT uq_prompt_name_version UNIQUE (PROMPT_NAME, VERSION)
);
```

`WIKI_PAGES` also has a `PROMPT_ID VARCHAR(36)` column added via `ALTER TABLE`. `NULL` = compiled before registry existed.

### How to update the prompt (no redeployment needed)
```sql
-- 1. Insert new version
INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.PROMPT_REGISTRY
  (PROMPT_NAME, VERSION, PROMPT_TEXT, IS_ACTIVE, NOTES)
VALUES
  ('wiki_compiler', 2, '... new prompt text ...', FALSE, 'My changes');

-- 2. Deactivate old version
UPDATE MANUFACTURING_WIKI.KNOWLEDGE.PROMPT_REGISTRY
SET IS_ACTIVE = FALSE WHERE VERSION = 1 AND PROMPT_NAME = 'wiki_compiler';

-- 3. Activate new version
UPDATE MANUFACTURING_WIKI.KNOWLEDGE.PROMPT_REGISTRY
SET IS_ACTIVE = TRUE WHERE VERSION = 2 AND PROMPT_NAME = 'wiki_compiler';
```

### SP lookup pattern (`02_ingest_pipeline.sql`)
```python
prompt_rows = session.sql(
    "SELECT PROMPT_ID, PROMPT_TEXT "
    "FROM MANUFACTURING_WIKI.KNOWLEDGE.PROMPT_REGISTRY "
    "WHERE PROMPT_NAME = 'wiki_compiler' AND IS_ACTIVE = TRUE "
    "ORDER BY VERSION DESC LIMIT 1"
).collect()
if not prompt_rows:
    return {"error": "No active prompt found in PROMPT_REGISTRY for 'wiki_compiler'. "
                     "Run the seed INSERT in 01_setup_infra.sql first."}
system_prompt = prompt_rows[0]["PROMPT_TEXT"]
prompt_id     = prompt_rows[0]["PROMPT_ID"]
```

---

## Cross-Reference Rules (restored in v1 prompt)

The `wiki_compiler` v1 prompt includes these inline linking rules:

```
CROSS-REFERENCE RULES:
- Machine (M-number, e.g. M045):          → See: equipment-m045-specs
- Production line (L-number, e.g. L3):    → See: production-l3-overview
- Maintenance Report OVERDUE task:         → See: fmea-m045-risks
- QC Report Cpk < 1.33:                   → See: maintenance-l3-log
- Chemical name or CHM-SKU:               → See: safety-[chemical-slug]-sds
- Supplier name or S-number:              → See: supplier-s012-directory
- Parts Catalog LOW STOCK + FMEA ref:     → See: fmea-m045-risks
- Place cross-references INLINE at END of the bullet they relate to.
- page_id format: all-lowercase, hyphens only, category-entity-descriptor
```

---

## Two-Lane Query Routing (`03_query_procedure.sql`)

```
User question
    │
    ▼
Classifier (COMPLETE call) → { "lane": "point_lookup" | "synthesis", "category": "...", "page_id": "..." }
    │
    ├── point_lookup: fetch single page → return content directly (no COMPLETE)
    │
    └── synthesis: Cortex Search (top-k pages) → COMPLETE → answer
```

**Known bug (unfixed)**: The synthesis lane applies a single `category` filter from the classifier. Cross-category questions (e.g., maintenance + qc) only retrieve pages from one category. Fix: drop the category filter for synthesis, or search both categories and merge results.

---

## Pending Tasks

### 1. Recompile 98 wiki pages (PRIORITY)
98 of 101 wiki pages have `PROMPT_ID IS NULL`, meaning they were compiled without the cross-reference instructions. They lack `→ See:` links.

**Audit query**:
```sql
SELECT COUNT(*) FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES WHERE PROMPT_ID IS NULL;
-- Returns: 98
```

**To recompile all**, loop over every DOC_ID in RAW_DOCUMENTS and call `COMPILE_WIKI_PAGE`. This will UPDATE existing pages with the new prompt, setting `PROMPT_ID` and adding cross-reference links.

```sql
-- Get all doc IDs to loop over
SELECT DOC_ID FROM MANUFACTURING_WIKI.KNOWLEDGE.RAW_DOCUMENTS ORDER BY DOC_ID;

-- Call for each:
CALL MANUFACTURING_WIKI.KNOWLEDGE.COMPILE_WIKI_PAGE('<doc_id>');
```

This takes ~30–60 minutes total (63 COMPLETE calls, ~1500 tokens each). Can be batched or run as a loop in a Snowflake task.

### 2. Fix synthesis lane category filter (KNOWN BUG)
Cross-category questions only pull from one category. Fix: in `03_query_procedure.sql`, drop the `category =` filter from the Cortex Search call in the synthesis lane, or pass multiple categories.

---

## Smoke Test (for verifying recompile worked)

```sql
-- After recompiling, verify cross-refs appeared
SELECT
  PAGE_ID,
  PROMPT_ID IS NOT NULL AS has_prompt_audit,
  CONTAINS(CONTENT_MD, '→ See:') AS has_cross_refs
FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES
ORDER BY UPDATED_AT DESC
LIMIT 10;
```

Expected: `has_prompt_audit = TRUE`, `has_cross_refs = TRUE` for all recompiled pages.

---

## Key Gotchas

1. **Do not use `snow sql -f`** for SPs with Python f-strings. Use `snowflake_sql_execute` tool directly — the CLI escapes braces and breaks f-string syntax.
2. **`claude-sonnet-4-5`** is the active model. `claude-3-5-sonnet` and `claude-3-5-sonnet-v2` are not available in this account.
3. **`PROMPT_ID IS NULL`** on old pages is intentional — it is an audit signal, not a bug.
4. **Only one `IS_ACTIVE = TRUE` row** should exist per `PROMPT_NAME` at a time. The SP uses `ORDER BY VERSION DESC LIMIT 1` as a safety net, but the intent is exactly one active row.
5. **Snowpark SP variables** inside SQL statements must use colon prefix (`:var_name`), not bare names — otherwise Snowflake treats them as column identifiers.
