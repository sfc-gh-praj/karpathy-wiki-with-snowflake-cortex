# Karpathy LLM-Wiki Pattern — Snowflake Manufacturing Demo

## Core Idea (from Karpathy's gist)

Standard RAG re-derives knowledge from raw documents on every query.
Karpathy's approach is different: an LLM **compiles** documents into a persistent,
structured wiki once, then queries are answered from that pre-built wiki.

> The wiki is a persistent, compounding artifact.
> Cross-references are already there. Contradictions already flagged.
> Synthesis already reflects everything ingested.

This demo applies that pattern to Snowflake — no Cortex Search, no vector embeddings.
Instead: `AI_PARSE_DOCUMENT` to read PDFs, `COMPLETE` to build the wiki,
Snowflake tables as the wiki store, and a Streamlit app as the interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Snowflake                                │
│                                                                 │
│  ┌──────────────┐    ┌────────────────────────────────────┐    │
│  │ Internal     │    │  MANUFACTURING_WIKI DB              │    │
│  │ Stage        │    │                                     │    │
│  │ @mfg_pdfs/   │    │  RAW_DOCUMENTS    (parsed text)     │    │
│  │              │───▶│  WIKI_PAGES       (compiled wiki)   │    │
│  │  *.pdf       │    │  WIKI_INDEX       (page catalog)    │    │
│  │              │    │  INGESTION_LOG    (audit trail)     │    │
│  └──────────────┘    └────────────────────────────────────┘    │
│                                           │                     │
│                              COMPLETE() + AI_PARSE_DOCUMENT()  │
│                                           │                     │
│                       ┌───────────────────▼──────────────────┐ │
│                       │   Streamlit App (SiS or local)        │ │
│                       │   - Ingest PDFs                       │ │
│                       │   - Browse Wiki                       │ │
│                       │   - Ask Questions                     │ │
│                       └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Three Layers (mapped from Karpathy)

| Karpathy Layer | Snowflake Equivalent |
|---|---|
| Raw sources (immutable) | `@MFG_STAGE` — uploaded PDFs |
| Wiki (LLM-maintained markdown) | `WIKI_PAGES` table — markdown rows per topic |
| Schema / CLAUDE.md | System prompts stored in `WIKI_SYSTEM_PROMPT` table |

---

## Manufacturing Demo — PDF Documents to Create

Seven PDFs covering different manufacturing domains, each using a different
layout/format to stress-test parsing.

### PDF 1 — Equipment Specification Sheet (`equipment_spec_CNC_X500.pdf`)
- Layout: datasheet style, two-column
- Content: CNC machine model X500 specs (RPM, axes, tolerances, weight, power draw)
- Includes: spec table, exploded-view diagram image, footnotes

### PDF 2 — Preventive Maintenance Report (`maintenance_report_Q1_2025.pdf`)
- Layout: report style, dense tables with multi-row headers
- Content: Q1 2025 maintenance schedule, tasks completed, parts replaced, technician IDs
- Includes: calendar table, parts replacement log, summary statistics table

### PDF 3 — Quality Control Dashboard (`qc_report_line_4_march.pdf`)
- Layout: dashboard-style with charts and KPIs
- Content: Line 4 defect rates, yield %, DPMO, Cpk values per product SKU
- Includes: bar chart image, SPC (control chart) image, KPI summary table

### PDF 4 — Safety Data Sheet — Lubricant (`sds_lubricant_ISO_VG_46.pdf`)
- Layout: GHS/OSHA SDS 16-section standard format
- Content: Chemical identity, hazard classification, first-aid, storage, PPE
- Includes: GHS pictogram images, hazard table, physical properties table

### PDF 5 — Production Run Log (`production_log_week_14_2025.pdf`)
- Layout: wide landscape table (many columns)
- Content: Hourly production counts by shift, machine ID, operator, downtime events
- Includes: multi-page wide table, shift summary totals

### PDF 6 — Supplier & Parts Catalog (`parts_catalog_fasteners.pdf`)
- Layout: catalog/grid with images per item
- Content: Fastener SKUs, dimensions, materials, unit price, lead time, supplier
- Includes: product thumbnail images, pricing table, compatibility matrix

### PDF 7 — Failure Mode & Effects Analysis (`fmea_assembly_line_5.pdf`)
- Layout: FMEA worksheet (extremely wide, nested headers)
- Content: Process steps, potential failure modes, effects, severity/occurrence/detection
  RPN scores, recommended actions
- Includes: nested header table, action ownership table

---

## Implementation Steps

### Phase 1 — Snowflake Infrastructure Setup

**Step 1.1 — Create database and schema**
```sql
CREATE DATABASE IF NOT EXISTS MANUFACTURING_WIKI;
CREATE SCHEMA IF NOT EXISTS MANUFACTURING_WIKI.KNOWLEDGE;
```

**Step 1.2 — Create internal stage for PDFs**
```sql
CREATE STAGE IF NOT EXISTS MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE
  DIRECTORY = (ENABLE = TRUE)
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');
```

**Step 1.3 — Create core tables**

```sql
-- Parsed raw document content from AI_PARSE_DOCUMENT
CREATE TABLE RAW_DOCUMENTS (
  DOC_ID        VARCHAR PRIMARY KEY,   -- derived from filename
  FILE_NAME     VARCHAR,
  STAGE_PATH    VARCHAR,
  PARSED_TEXT   VARIANT,               -- full AI_PARSE_DOCUMENT output (JSON)
  PLAIN_TEXT    TEXT,                  -- extracted flat text for LLM consumption
  PAGE_COUNT    INT,
  INGESTED_AT   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Wiki pages compiled by COMPLETE() — one row per topic/entity/concept
CREATE TABLE WIKI_PAGES (
  PAGE_ID       VARCHAR PRIMARY KEY,   -- slug, e.g. 'cnc-x500-specs'
  PAGE_TITLE    VARCHAR,
  CATEGORY      VARCHAR,               -- e.g. 'equipment', 'process', 'safety', 'supplier'
  CONTENT_MD    TEXT,                  -- full markdown body
  SOURCE_DOCS   ARRAY,                 -- list of DOC_IDs that contributed
  VERSION       INT DEFAULT 1,
  CREATED_AT    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  UPDATED_AT    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Flat index of all wiki pages (used instead of Cortex Search)
CREATE TABLE WIKI_INDEX (
  PAGE_ID       VARCHAR,
  PAGE_TITLE    VARCHAR,
  CATEGORY      VARCHAR,
  ONE_LINE_SUMMARY  VARCHAR,           -- LLM-generated one-liner
  KEYWORDS      ARRAY,                 -- LLM-extracted keywords for lookup
  UPDATED_AT    TIMESTAMP_NTZ
);

-- Append-only log of all operations (ingest / query / lint)
CREATE TABLE INGESTION_LOG (
  LOG_ID        VARCHAR DEFAULT UUID_STRING(),
  OPERATION     VARCHAR,               -- 'ingest' | 'query' | 'lint' | 'wiki_update'
  DOC_ID        VARCHAR,
  DETAIL        TEXT,
  PERFORMED_AT  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

---

### Phase 2 — Generate the Seven Demo PDFs (Python, local)

Use Python with `reportlab` and `fpdf2` libraries.
Each script produces one PDF matching the layout described above.

**Requirements**
```
pip install reportlab fpdf2 Pillow matplotlib
```

**Script structure** — one file per PDF in `pdf_generators/`:
```
pdf_generators/
  01_equipment_spec.py
  02_maintenance_report.py
  03_qc_dashboard.py
  04_safety_data_sheet.py
  05_production_log.py
  06_parts_catalog.py
  07_fmea_worksheet.py
  generate_all.py          # runs all seven
```

Each script must produce a realistic, dense document:
- Real field names and plausible manufacturing data
- At least one embedded image (matplotlib chart or drawn diagram)
- At least one data table
- Multiple pages where appropriate

**Upload to stage after generation**
```bash
snow stage copy ./pdfs/ @MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE --overwrite
```

---

### Phase 3 — Ingest Pipeline (Snowpark Python Stored Procedure)

**Step 3.1 — Parse PDFs using AI_PARSE_DOCUMENT**

```sql
-- For each file in stage, call AI_PARSE_DOCUMENT and store result
INSERT INTO RAW_DOCUMENTS (DOC_ID, FILE_NAME, STAGE_PATH, PARSED_TEXT, PLAIN_TEXT, PAGE_COUNT)
SELECT
  REGEXP_REPLACE(RELATIVE_PATH, '[^a-zA-Z0-9]', '_') AS DOC_ID,
  RELATIVE_PATH AS FILE_NAME,
  BUILD_STAGE_FILE_URL(@MFG_STAGE, RELATIVE_PATH) AS STAGE_PATH,
  SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT(
    @MFG_STAGE,
    RELATIVE_PATH,
    {'mode': 'LAYOUT'}             -- LAYOUT mode preserves tables and structure
  ) AS PARSED_TEXT,
  PARSED_TEXT['content']::TEXT AS PLAIN_TEXT,
  PARSED_TEXT['numPages']::INT AS PAGE_COUNT
FROM DIRECTORY(@MFG_STAGE)
WHERE RELATIVE_PATH LIKE '%.pdf'
  AND RELATIVE_PATH NOT IN (SELECT FILE_NAME FROM RAW_DOCUMENTS);
```

**Step 3.2 — Compile wiki pages from parsed documents (COMPLETE)**

For each newly ingested document, call COMPLETE with a structured prompt:

```sql
-- Snowpark stored procedure: INGEST_TO_WIKI(doc_id VARCHAR)
-- Reads PLAIN_TEXT, calls COMPLETE to produce structured wiki content
-- Upserts into WIKI_PAGES and updates WIKI_INDEX
```

The LLM prompt instructs it to:
1. Identify entities, machines, processes, chemicals mentioned
2. Write a summary wiki page for the document
3. List cross-references to likely existing pages
4. Produce a one-line summary and keyword list for the index

**Step 3.3 — Update WIKI_INDEX after each ingest**

```sql
MERGE INTO WIKI_INDEX AS target
USING (
  SELECT PAGE_ID, PAGE_TITLE, CATEGORY,
    SNOWFLAKE.CORTEX.COMPLETE('claude-4', ...) AS ONE_LINE_SUMMARY,
    ...
  FROM WIKI_PAGES WHERE PAGE_ID = :new_page_id
) AS source ON target.PAGE_ID = source.PAGE_ID
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...;
```

---

### Phase 4 — Query Flow (No Vector Search)

Karpathy's insight: at moderate scale, a flat index + LLM reading is enough.

**Query steps:**
1. User submits question via Streamlit
2. App calls `ANSWER_QUESTION(question)` stored procedure
3. Procedure calls `COMPLETE` with the WIKI_INDEX content +
   the question → LLM picks 3-5 relevant PAGE_IDs
4. Procedure fetches full `CONTENT_MD` for those pages
5. Second `COMPLETE` call synthesises answer from page content
6. Answer + citations (page titles + source doc filenames) returned
7. Optionally: file the answer back as a new WIKI_PAGE (compounding)

```
User Question
     │
     ▼
COMPLETE(index_summary + question) ──▶ [page_id_1, page_id_2, page_id_3]
     │
     ▼
Fetch WIKI_PAGES WHERE PAGE_ID IN (...)
     │
     ▼
COMPLETE(page_content_1 + page_content_2 + page_content_3 + question)
     │
     ▼
Answer + Citations
```

No embeddings. No vector store. No Cortex Search.

---

### Phase 5 — Streamlit App

**App pages / tabs:**

#### Tab 1 — Query
- Text input for question
- "Ask" button → calls stored procedure
- Shows answer in markdown
- Shows citations (source PDF filenames, wiki page titles)
- "Save to Wiki" button to persist the answer as a new page

#### Tab 2 — Wiki Browser
- Category filter (equipment, process, safety, supplier, analysis)
- Table of pages from WIKI_INDEX
- Click page → renders CONTENT_MD as markdown
- Shows source documents that contributed

#### Tab 3 — Ingest
- List of PDFs in stage (from DIRECTORY(@MFG_STAGE))
- Checkboxes to select
- "Ingest Selected" → calls INGEST_TO_WIKI per file
- Progress bar via st.progress
- Shows INGESTION_LOG tail

#### Tab 4 — Wiki Health (Lint)
- Calls a LINT_WIKI stored procedure
- COMPLETE reviews all pages for: contradictions, orphan pages,
  stale claims, missing cross-references
- Returns a lint report rendered as markdown

---

### Phase 6 — Key Snowflake Functions Used

| Function | Purpose |
|---|---|
| `AI_PARSE_DOCUMENT(@stage, path, {'mode':'LAYOUT'})` | Extract text + table structure from PDFs, handles images via OCR |
| `SNOWFLAKE.CORTEX.COMPLETE(model, prompt)` | LLM calls for wiki compilation and query answering |
| `DIRECTORY(@stage)` | List files in stage |
| `BUILD_STAGE_FILE_URL()` | Construct URLs for stage files |
| Snowpark Python SP | Orchestration logic for ingest + query pipelines |

---

### Why No Cortex Search?

Cortex Search uses embedding-based chunk retrieval — it re-derives answers
from raw chunks every query (classic RAG). This demo follows Karpathy's
alternative: pre-compile documents into a structured wiki, query the
compiled knowledge. The wiki gets richer with every ingest.
The trade-off: more upfront work per document, but better synthesis,
cross-referencing, and compounding value over time.

---

## File Layout (Final)

```
karpathy-workflow/
  plan.md                          ← this file
  pdf_generators/
    01_equipment_spec.py
    02_maintenance_report.py
    03_qc_dashboard.py
    04_safety_data_sheet.py
    05_production_log.py
    06_parts_catalog.py
    07_fmea_worksheet.py
    generate_all.py
  pdfs/                            ← generated PDFs go here
  snowflake/
    01_setup_infra.sql             ← DB, schema, stage, tables
    02_ingest_pipeline.sql         ← AI_PARSE_DOCUMENT + COMPLETE calls
    03_query_procedure.sql         ← ANSWER_QUESTION stored procedure
    04_lint_procedure.sql          ← LINT_WIKI stored procedure
  streamlit/
    app.py                         ← main Streamlit app
    utils/
      snowflake_conn.py            ← session/connection helpers
      wiki_ops.py                  ← ingest, query, lint wrappers
```

---

## Next Steps (in order)

1. Generate the seven PDFs locally (Phase 2 Python scripts)
2. Run `01_setup_infra.sql` to create Snowflake objects
3. Upload PDFs to `@MFG_STAGE`
4. Run `02_ingest_pipeline.sql` to parse and compile wiki
5. Run `03_query_procedure.sql` to create query SP
6. Build and test `streamlit/app.py` locally against Snowflake
7. Optionally deploy as Streamlit in Snowflake (SiS)
