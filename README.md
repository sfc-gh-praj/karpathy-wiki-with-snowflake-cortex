# Karpathy Wiki with Snowflake Cortex

A Karpathy-inspired LLM wiki pattern built natively on Snowflake. Raw PDF documents are parsed, compiled into structured wiki pages by an LLM, indexed for semantic search, and made queryable through a two-lane question-answering system — all without leaving Snowflake.

---

## What it does

| Stage | What happens |
|---|---|
| **Ingest** | PDFs uploaded to an internal stage are parsed with `AI_PARSE_DOCUMENT` |
| **Compile** | An LLM (Claude) reads each parsed document and writes structured wiki pages in Markdown |
| **Index** | Wiki pages are indexed by `CORTEX SEARCH SERVICE` for semantic retrieval |
| **Answer** | User questions are routed to one of two lanes — point lookup or synthesis — and answered using retrieved wiki pages |
| **UI** | A Streamlit in Snowflake app provides a chat-style Q&A interface plus wiki browse and document management |

---

## Architecture

```
PDFs (uploaded to @MFG_STAGE)
        │
        ▼
PARSE_NEW_DOCUMENTS SP
  └─► AI_PARSE_DOCUMENT → RAW_DOCUMENTS table
        │
        ▼
COMPILE_WIKI_PAGE SP
  └─► CORTEX.COMPLETE (claude-sonnet-4-5) → WIKI_PAGES + WIKI_INDEX tables
        │
        ▼
WIKI_SEARCH (Cortex Search Service)
  └─► ON CONTENT_MD, attributes PAGE_ID, CATEGORY
        │
        ▼
ANSWER_QUESTION SP
  ├─► classify lane (point_lookup | synthesis)
  ├─► point_lookup: Cortex Search top-1 page → return directly
  └─► synthesis: Cortex Search top-N pages → CORTEX.COMPLETE → synthesised answer
        │
        ▼
Streamlit in Snowflake (SiS) UI
```

---

## Document types

The `pdf_generators/` directory generates synthetic manufacturing PDFs across seven document types:

| Type | Description |
|---|---|
| `production_log` | Shift-by-shift production output, OEE, and downtime per line |
| `maintenance_report` | Equipment maintenance history and task logs |
| `qc_report` | Quality control inspection results |
| `equipment_spec` | Machine specifications and parameters |
| `safety_data_sheet` | Chemical SDS with storage and handling requirements |
| `parts_catalog` | Supplier parts with lead times and pricing |
| `fmea_worksheet` | Failure mode and effects analysis |

---

## Two-lane query system

Questions are classified before retrieval:

**Point lookup** — a single factual question about one entity  
- Cortex Search returns the single most relevant wiki page  
- No LLM synthesis call — answer comes directly from the page  
- Latency: ~200 ms

**Synthesis** — a cross-document question requiring comparison or aggregation  
- Cortex Search returns the top N wiki pages (default 8, configurable)  
- No category filter — searches across all categories to avoid missing relevant pages  
- LLM synthesises a new answer by reasoning across all retrieved pages  
- Latency: ~10–40 s

Example questions:
- *"What is the OEE target for Line L7?"* → point lookup (one page)
- *"Which production line had the highest downtime this week?"* → synthesis (8 pages, 5 lines compared)

---

## Repository structure

```
├── snowflake/
│   ├── 01_setup_infra.sql        # Tables, stage, search service, prompt registry
│   ├── 02_ingest_pipeline.sql    # PARSE_NEW_DOCUMENTS + INGEST_ALL_NEW SPs
│   ├── 03_query_procedure.sql    # ANSWER_QUESTION SP (two-lane router)
│   └── 04_lint_procedure.sql     # LINT_WIKI SP — LLM quality check on wiki
│
├── streamlit/
│   ├── app.py                    # Streamlit in Snowflake app
│   ├── utils/wiki_ops.py         # SP wrappers and helper functions
│   ├── pyproject.toml            # SiS Python dependencies
│   └── snowflake.yml             # SiS deployment config
│
├── pdf_generators/               # Synthetic PDF generation scripts
│   ├── generate_all.py           # Entry point — generates all PDF types
│   └── doc_types/                # One module per document type
│
├── requirements.txt              # Local dev dependencies
└── claude.md                     # Project constraints and lessons learned
```

---

## Prerequisites

- Snowflake account with Cortex features enabled (`SNOWFLAKE.CORTEX.COMPLETE`, `AI_PARSE_DOCUMENT`, Cortex Search)
- Snow CLI installed and configured
- Python 3.11+ (for local PDF generation only)
- Role with `CREATE DATABASE`, `CREATE PROCEDURE`, `CREATE CORTEX SEARCH SERVICE` privileges

---

## Setup

### 1. Generate synthetic PDFs (optional)

If you want to use the included manufacturing dataset:

```bash
pip install -r requirements.txt
python pdf_generators/generate_all.py
```

PDFs are written to `pdfs/`.

### 2. Upload PDFs to Snowflake stage

```bash
snow stage copy pdfs/ @MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE --connection COCO_JK
```

### 3. Run infrastructure setup

```bash
snow sql -f snowflake/01_setup_infra.sql --connection COCO_JK
```

This creates:
- `MANUFACTURING_WIKI` database and `KNOWLEDGE` schema
- `RAW_DOCUMENTS`, `WIKI_PAGES`, `WIKI_INDEX`, `PROMPT_REGISTRY`, `INGESTION_LOG` tables
- `@MFG_STAGE` internal stage
- `WIKI_SEARCH` Cortex Search Service

### 4. Deploy stored procedures

```bash
snow sql -f snowflake/02_ingest_pipeline.sql --connection COCO_JK
snow sql -f snowflake/03_query_procedure.sql --connection COCO_JK
snow sql -f snowflake/04_lint_procedure.sql  --connection COCO_JK
```

> **Note:** Always use `snow sql -f` (not `snow sql -q`) for Python stored procedures. Inline shell quoting strips Python list literals and causes silent runtime failures.

### 5. Ingest and compile

```bash
# Parse PDFs → RAW_DOCUMENTS
snow sql -q "CALL MANUFACTURING_WIKI.KNOWLEDGE.PARSE_NEW_DOCUMENTS(50)" --connection COCO_JK

# Compile RAW_DOCUMENTS → WIKI_PAGES + WIKI_INDEX
snow sql -q "CALL MANUFACTURING_WIKI.KNOWLEDGE.INGEST_ALL_NEW(50)" --connection COCO_JK
```

### 6. Deploy the Streamlit app

```bash
cd streamlit
snow streamlit deploy --replace --connection COCO_JK
```

---

## Stored procedures reference

| Procedure | Signature | Purpose |
|---|---|---|
| `PARSE_NEW_DOCUMENTS` | `(MAX_FILES NUMBER)` | Parse PDFs via `AI_PARSE_DOCUMENT`, write to `RAW_DOCUMENTS` |
| `COMPILE_WIKI_PAGE` | `(DOC_ID VARCHAR)` | Compile one document into wiki page(s) |
| `INGEST_ALL_NEW` | `(MAX_FILES NUMBER)` | Parse + compile all unprocessed documents |
| `COMPILE_ALL_WIKI` | `(MAX_DOCS NUMBER)` | Recompile all documents (use sparingly — see notes) |
| `RECOMPILE_REMAINING` | `()` | Compile only documents with no existing pages |
| `ANSWER_QUESTION` | `(QUESTION VARCHAR, MAX_CONTEXT_PAGES NUMBER DEFAULT 8)` | Two-lane Q&A |
| `LINT_WIKI` | `()` | LLM quality audit of all wiki pages |

---

## Streamlit UI

The app has three tabs:

**Ask** — natural language Q&A with lane indicator, latency, source wiki pages, and source PDF traceability

**Wiki** — browse all compiled wiki pages by category, view full page content

**Ingest** — upload and manage documents, trigger ingestion, view ingestion log

---

## Key design notes

See `claude.md` for the full list of lessons learned. Key points:

- **Streamlit in Snowflake** runs an older pinned Streamlit version — `st.container(horizontal=True)`, `st.column_config`, `st.dataframe(hide_index=True)`, `st.rerun()` and several other newer APIs are not available
- **Model**: use `claude-sonnet-4-5` — `claude-3-5-sonnet` is not available in this account
- **Snowpark parameterised queries**: use `session.sql(q, params=[...])` — `.bind()` does not exist
- **Synthesis lane**: `search_filter = None` — do not add a category filter, or cross-category retrieval breaks
- **`COMPILE_ALL_WIKI`**: do not re-run on already-compiled documents — LLM generates non-deterministic `page_id` values, creating orphaned duplicate pages

---

## License

MIT
