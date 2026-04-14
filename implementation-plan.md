# Karpathy LLM-Wiki — Manufacturing Demo: Full Implementation Plan

## Overview

Apply Karpathy's LLM-Wiki pattern to 500 manufacturing PDFs in Snowflake.
Instead of RAG (re-derive on every query), the LLM **compiles** documents into
a persistent wiki once. Queries are answered from pre-built, cross-referenced
knowledge — no Cortex Search on raw chunks.

---

## Final File Structure

```
karpathy-workflow/
  requirements.txt
  implementation-plan.md             ← this file

  pdf_generators/
    data_generator.py                ← shared Faker data factory
    doc_types/
      equipment_spec.py              ← Type 1: 80 PDFs, 50-60 pages
      maintenance_report.py          ← Type 2: 80 PDFs, 60-80 pages
      qc_report.py                   ← Type 3: 70 PDFs, 55-70 pages
      safety_data_sheet.py           ← Type 4: 70 PDFs, 50-55 pages
      production_log.py              ← Type 5: 70 PDFs, 80-100 pages
      parts_catalog.py               ← Type 6: 65 PDFs, 70-90 pages
      fmea_worksheet.py              ← Type 7: 65 PDFs, 60-75 pages
    generate_all.py                  ← orchestrator with multiprocessing

  pdfs/                              ← 500 generated PDFs

  snowflake/
    01_setup_infra.sql               ← DB, schema, stage, 4 tables
    02_ingest_pipeline.sql           ← AI_PARSE_DOCUMENT + COMPLETE wiki SP
    03_query_procedure.sql           ← ANSWER_QUESTION SP (two-lane routing)
    04_lint_procedure.sql            ← LINT_WIKI SP

  streamlit/
    app.py                           ← Streamlit in Snowflake app (4 tabs)
    utils/
      wiki_ops.py                    ← ingest / query / lint wrappers

  diagrams/
    flow_diagram.py                  ← generates architecture.png
    animated_flow.py                 ← generates karpathy_wiki_flow.gif

  output/
    architecture.png                 ← static flow diagram
    karpathy_wiki_flow.gif           ← animated end-to-end GIF
```

---

## Phase 1 — PDF Generation

### Manufacturing Universe (consistent across all 500 PDFs)

Seeded with Faker so data is internally consistent per document:
- **200 machines**: M001–M200, each with model, production line, bay, install date, supplier
- **10 production lines**: L1–L10
- **20 suppliers**: S001–S020 with lead times, part categories
- **50 chemical/lubricant SKUs**
- **30 technicians**: names + employee IDs

### 7 Document Types

| Type | Count | Pages | Key Layout Features |
|---|---|---|---|
| Equipment Spec | 80 | 50-60 | Two-column datasheet, spec table, matplotlib diagram |
| Maintenance Report | 80 | 60-80 | Multi-row header tables, parts log, summary stats |
| QC Report | 70 | 55-70 | matplotlib bar chart + SPC chart, KPI boxes |
| Safety Data Sheet | 70 | 50-55 | GHS 16-section, hazard table, pictograms |
| Production Log | 70 | 80-100 | Wide landscape table, multi-page, shift summaries |
| Parts Catalog | 65 | 70-90 | Grid with images, pricing table |
| FMEA Worksheet | 65 | 60-75 | Nested header table, RPN scores, action log |

**Total: 500 PDFs, ~37,500 average pages**

### Generation Strategy
- `multiprocessing.Pool` with 8 workers → ~5-8 min total
- Each PDF seeded with its index for reproducibility
- `tqdm` progress bar

---

## Phase 2 — Snowflake Infrastructure

### Tables

```sql
RAW_DOCUMENTS
  DOC_ID        VARCHAR PK
  FILE_NAME     VARCHAR
  STAGE_PATH    VARCHAR
  PARSED_TEXT   VARIANT        -- AI_PARSE_DOCUMENT output
  PLAIN_TEXT    TEXT           -- flat extracted text
  PAGE_COUNT    INT
  INGESTED_AT   TIMESTAMP_NTZ

WIKI_PAGES
  PAGE_ID       VARCHAR PK     -- slug: 'equipment-M042-specs'
  PAGE_TITLE    VARCHAR
  CATEGORY      VARCHAR        -- equipment|maintenance|qc|safety|production|supplier|fmea
  CONTENT_MD    TEXT           -- full markdown body
  SOURCE_DOCS   ARRAY          -- contributing DOC_IDs
  VERSION       INT
  CREATED_AT    TIMESTAMP_NTZ
  UPDATED_AT    TIMESTAMP_NTZ

WIKI_INDEX
  PAGE_ID           VARCHAR
  PAGE_TITLE        VARCHAR
  CATEGORY          VARCHAR
  ONE_LINE_SUMMARY  VARCHAR
  KEYWORDS          ARRAY
  UPDATED_AT        TIMESTAMP_NTZ

INGESTION_LOG
  LOG_ID        VARCHAR DEFAULT UUID_STRING()
  OPERATION     VARCHAR        -- ingest|query|lint|wiki_update
  DOC_ID        VARCHAR
  DETAIL        TEXT
  PERFORMED_AT  TIMESTAMP_NTZ
```

---

## Phase 3 — Ingest Pipeline

### First Load
1. Upload all 500 PDFs to `@MFG_STAGE`
2. `PARSE_NEW_DOCUMENTS()` — calls `AI_PARSE_DOCUMENT(LAYOUT mode)` per PDF
3. `COMPILE_WIKI(doc_id)` per document — `COMPLETE` with domain schema prompt
4. Produces wiki pages per entity (machine page, supplier page, etc.)

### Incremental Load
- `PARSE_NEW_DOCUMENTS()` skips already-ingested files
- `COMPILE_WIKI(new_doc_id)` processes only the new document
- Updates relevant existing wiki pages (e.g. machine M042 page updated when new maintenance report arrives)
- Appends to `INGESTION_LOG`

### Manufacturing Domain Schema Prompt (embedded in SP)
Tells the LLM what to extract:
- Entities: machines, suppliers, production lines, chemicals
- Always extract: machine IDs, dates, numeric values + units, technician IDs
- Red flags: overdue maintenance, defect rate >2.5%, FMEA severity >7, storage conflicts
- Cross-references: maintenance → machine, QC → line + machines, supplier → machines
- Contradictions: SDS vs procedure, spec vs measured values

---

## Phase 4 — Query Flow (Two-Lane)

```
Question
   │
   ▼
COMPLETE → classify: "point_lookup" or "synthesis"
   │                          │
   ▼                          ▼
Cortex Search           Read WIKI_INDEX
over WIKI_PAGES         COMPLETE picks page IDs
with ATTRIBUTES         Fetch pages
   │                    COMPLETE synthesises
   ▼                          │
Top 3 pages             Answer + Citations
   │                          │
COMPLETE → Answer        ◄────┘
```

Returns: `{answer, citations, lane_used, wiki_pages_read, latency_ms}`

---

## Phase 5 — Streamlit in Snowflake App

### Tab 1 — Ask
- Text input, Ask button
- Answer in markdown + citations
- Lane indicator (point lookup vs synthesis)
- "Save to Wiki" button

### Tab 2 — Wiki Browser
- Category filter
- Table of WIKI_INDEX rows
- Click → full CONTENT_MD rendered

### Tab 3 — Ingest
- List PDFs in stage
- Checkbox select → "Ingest Selected"
- st.progress bar + live INGESTION_LOG tail

### Tab 4 — Wiki Health
- "Run Lint" button → LINT_WIKI SP
- Renders lint report (contradictions, orphans, gaps)

---

## Phase 6 — Visuals

### Static Flow Diagram (architecture.png)
matplotlib figure with 3 panels:
1. Full system architecture
2. First load flow
3. Incremental load flow

### Animated GIF (karpathy_wiki_flow.gif)
~90 frames at 12fps (~7.5 second loop), 5 scenes:
1. **PDFs in stage** (frames 1-15): 500 PDF boxes appear by type
2. **Parse** (frames 16-35): scanning arrow, RAW_DOCUMENTS fills
3. **Wiki build** (frames 36-55): COMPLETE processes, wiki pages fly into table
4. **Query flow** (frames 56-72): question → index → pages highlight → answer
5. **Incremental** (frames 73-90): single PDF drops in, only delta processed

---

## Execution Order

1. Install reportlab, tqdm
2. Create data_generator.py
3. Create 7 PDF doc type modules
4. Create generate_all.py
5. Run: `python pdf_generators/generate_all.py` (~5-8 min)
6. Create Snowflake SQL files
7. Create Streamlit app
8. Create diagrams (flow_diagram.py, animated_flow.py)
9. Run diagrams: `python diagrams/flow_diagram.py && python diagrams/animated_flow.py`
10. Upload PDFs to stage and run SQL
