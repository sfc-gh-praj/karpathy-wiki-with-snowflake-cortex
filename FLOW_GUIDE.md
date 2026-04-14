# Manufacturing Wiki — Data Engineer's Flow Guide

> This guide explains the full pipeline from raw PDFs to answered questions.
> No prior knowledge of the project or Karpathy's pattern is assumed.

---

## 1. The Problem This Solves

Imagine you have 63 manufacturing PDFs — equipment specs, maintenance reports, QC reports,
safety data sheets, FMEA worksheets, parts catalogs, and production logs. You need to answer
questions like:

- "What is the power rating of machine M015?"
- "Which production lines have both overdue maintenance AND Cpk below 1.33?"
- "What PPE does Solvent Grade 41 require?"

The naive approach is **RAG (Retrieval-Augmented Generation)**:
1. Chunk each PDF into paragraphs
2. Embed chunks into a vector store
3. At query time, find the nearest chunks and feed them to an LLM

**Why RAG falls short here:**
- Chunks are fragments. A question about "machine M015 on Line L4" needs facts scattered
  across an equipment spec, a maintenance report, and a QC report — three different PDFs,
  none of which reference each other.
- The LLM sees raw OCR text with tables as pipe-delimited strings, not structured facts.
- Every question pays full LLM inference cost even for simple lookups.

---

## 2. The Karpathy Pattern — Pre-compile the Knowledge

The insight (from Andrej Karpathy's writing on LLM workflows) is:

> **Don't answer from raw chunks. Answer from a wiki you compiled offline.**

Instead of feeding raw PDF text to the LLM at query time, you do an offline compilation step:

```
PDFs  ──►  AI_PARSE_DOCUMENT  ──►  RAW_DOCUMENTS  ──►  COMPLETE  ──►  WIKI_PAGES
                                    (raw text)         (offline)       (structured facts)
                                                                             │
                                                                     Cortex Search
                                                                             │
                                                                       ANSWER_QUESTION
```

The LLM runs once per document at ingest time to extract and structure the knowledge.
At query time, you either return a wiki page directly (fast, free) or combine a few pages
with a second LLM call (slower, but operating on structured facts, not raw OCR).

---

## 3. Files in This Project

```
karpathy-workflow/
│
├── pdf_generators/                    ← Python scripts that generate synthetic PDFs
│   ├── generate_all.py                   Entry point: python generate_all.py --count 50 --pages 20
│   ├── data_generator.py                 Faker-based data model (machines, lines, chemicals)
│   └── doc_types/
│       ├── equipment_spec.py             Generates equipment specification PDFs
│       ├── maintenance_report.py         Generates PM / maintenance report PDFs
│       ├── qc_report.py                  Generates quality control report PDFs
│       ├── safety_data_sheet.py          Generates GHS-format SDS PDFs
│       ├── fmea_worksheet.py             Generates FMEA worksheet PDFs
│       ├── parts_catalog.py              Generates parts catalog PDFs
│       └── production_log.py             Generates production log PDFs
│
└── snowflake/
    ├── 01_setup_infra.sql             Creates database, schema, stage, tables
    ├── 02_ingest_pipeline.sql         SPs: PARSE_NEW_DOCUMENTS, COMPILE_WIKI_PAGE, INGEST_ALL_NEW
    ├── 03_query_procedure.sql         SP: ANSWER_QUESTION (two-lane routing)
    └── 04_lint_procedure.sql          SP: LINT_WIKI + Cortex Search service
```

---

## 4. Tables and What They Hold

```
@MFG_STAGE          Raw PDF files (63 files, ~2–3 MB each)
      │
      ▼
RAW_DOCUMENTS       One row per PDF. Columns:
                      DOC_ID       — 'equipment_spec_0002'
                      FILE_NAME    — 'equipment_spec_0002.pdf'
                      PLAIN_TEXT   — flat extracted text (~25K chars per doc)
                      PARSED_TEXT  — full AI_PARSE_DOCUMENT JSON (tables preserved)
                      DOC_TYPE     — 'equipment_spec' | 'maintenance' | 'qc' | ...
                      PAGE_COUNT   — number of pages
      │
      ▼
WIKI_PAGES          One row per entity or topic. Columns:
                      PAGE_ID      — 'equipment-m015-okuma-4372'
                      PAGE_TITLE   — 'Okuma-4372 (M015) Equipment Overview'
                      CATEGORY     — 'equipment' | 'maintenance' | 'qc' | ...
                      CONTENT_MD   — structured markdown (bullets, key facts, ALERT flags)
                      SOURCE_DOCS  — ['equipment_spec_0002']  ← which RAW_DOCUMENTS fed this
                      VERSION      — increments each time a new doc updates the page

WIKI_INDEX          One row per wiki page — compact catalog for routing. Columns:
                      PAGE_ID, PAGE_TITLE, CATEGORY
                      ONE_LINE_SUMMARY   — 'Punch press M015 on L4, 38 kW, supplier Siemens'
                      KEYWORDS           — ['M015', 'Okuma', 'L4', 'punch press', 'Siemens']
                      SOURCE_DOC_COUNT   — how many PDFs contributed to this page

INGESTION_LOG       Append-only audit trail. One row per operation:
                      OPERATION    — 'ingest' | 'wiki_compile' | 'query'
                      DOC_ID       — which document
                      STATUS       — 'success' | 'error'
                      DURATION_MS  — how long it took

WIKI_SAVED_ANSWERS  Every answered question stored here. Columns:
                      QUESTION     — the original question
                      ANSWER_MD    — the answer in markdown
                      CITATIONS    — ['page-id-1', 'page-id-2']  ← source wiki pages
                      LANE_USED    — 'point_lookup' | 'synthesis'
```

---

## 5. Step-by-Step: How a PDF Becomes an Answer

### Step A — Generate PDFs (local, Python)

```bash
cd pdf_generators
python generate_all.py --count 50 --pages 20
```

`generate_all.py` calls each doc type generator (e.g. `equipment_spec.py`) with a random
seed. Each generator uses `data_generator.py` to invent consistent entities — machine IDs,
line numbers, supplier names, part numbers — and renders them into a PDF with reportlab.

**Output:** `output/equipment_spec_0000.pdf` ... `output/fmea_worksheet_0062.pdf`

---

### Step B — Upload to Snowflake Stage

```bash
snow stage copy output/*.pdf @MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE
```

This puts the raw PDFs into `@MFG_STAGE`. Nothing in Snowflake knows their content yet.

---

### Step C — Parse PDFs into RAW_DOCUMENTS

**Stored procedure:** `PARSE_NEW_DOCUMENTS` (in `02_ingest_pipeline.sql`, line 9)

```sql
CALL MANUFACTURING_WIKI.KNOWLEDGE.PARSE_NEW_DOCUMENTS(10);
```

**What it does, line by line:**

1. Query `RAW_DOCUMENTS` to get files already processed (incremental — never re-parses)
2. Query `DIRECTORY(@MFG_STAGE)` to list all PDFs in the stage
3. For each new file, call `AI_PARSE_DOCUMENT`:

   ```sql
   SELECT SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT(
       TO_FILE('@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE', 'equipment_spec_0002.pdf'),
       {'mode': 'LAYOUT'}
   ) AS parsed
   ```

   `TO_FILE()` is critical — it returns a proper `FILE` type. `BUILD_SCOPED_FILE_URL`
   returns a `VARCHAR` and causes a type error. `LAYOUT` mode preserves table structure.

4. Extract `content` (flat text) and `numPages` from the JSON result
5. INSERT into `RAW_DOCUMENTS`

**After this step:** `RAW_DOCUMENTS` has 63 rows, one per PDF.
The `PLAIN_TEXT` column holds ~25K characters of extracted text per document.

---

### Step D — Compile Wiki Pages from RAW_DOCUMENTS

**Stored procedure:** `COMPILE_WIKI_PAGE` (in `02_ingest_pipeline.sql`, line 120)

```sql
CALL MANUFACTURING_WIKI.KNOWLEDGE.COMPILE_WIKI_PAGE('equipment_spec_0002');
```

**What it does:**

1. Fetch `PLAIN_TEXT` from `RAW_DOCUMENTS` for this `DOC_ID`
2. Truncate to 15K chars (keeps cost and latency predictable)
3. Build a structured prompt with extraction rules (IDs, units, ALERT flags,
   cross-references)
4. Call `claude-sonnet-4-5` via `COMPLETE` using a CTE to pass the large prompt:

   ```sql
   WITH p AS (SELECT ? AS prompt)
   SELECT SNOWFLAKE.CORTEX.COMPLETE(
       'claude-sonnet-4-5',
       [{'role': 'user', 'content': p.prompt}],
       {'max_tokens': 1500}
   ) AS wiki_json FROM p
   ```

   The CTE approach avoids Snowpark parameter size limits for large strings.
   `max_tokens: 1500` prevents the JSON response being truncated mid-brace.

5. Parse the JSON response. Extract the `wiki_pages` array.
6. For each page: UPSERT into `WIKI_PAGES`, MERGE into `WIKI_INDEX`.

**After this step:** `WIKI_PAGES` has 98 rows across 7 categories.

---

### Step E — Index with Cortex Search

**Service:** `WIKI_SEARCH` (created in `04_lint_procedure.sql`)

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE MANUFACTURING_WIKI.KNOWLEDGE.WIKI_SEARCH
  ON CONTENT_MD
  ATTRIBUTES CATEGORY, PAGE_ID
  WAREHOUSE = QUICKSTART
  TARGET_LAG = '1 hour'
AS (
  SELECT p.PAGE_ID, p.PAGE_TITLE, p.CATEGORY, p.CONTENT_MD, i.ONE_LINE_SUMMARY
  FROM WIKI_PAGES p JOIN WIKI_INDEX i USING (PAGE_ID)
);
```

This embeds every `CONTENT_MD` using `snowflake-arctic-embed-m-v1.5`.
At query time, Cortex Search does semantic + keyword hybrid retrieval in milliseconds.

---

### Step F — Answer a Question

**Stored procedure:** `ANSWER_QUESTION` (in `03_query_procedure.sql`)

```sql
CALL MANUFACTURING_WIKI.KNOWLEDGE.ANSWER_QUESTION('Your question here');
```

This is where the two-lane routing happens.

---

## 6. The Two Lanes — With Real Examples

### Lane 1: point_lookup

**When to use:** One entity, one fact. The answer lives in a single wiki page.

**Example question:** `"What PPE is required for Solvent Grade 41?"`

```
ANSWER_QUESTION called
        │
        ▼
[Classify] claude-sonnet-4-5 sees: "What PPE is required for Solvent Grade 41?"
           → returns: "point_lookup"
           → category: "safety"
        │
        ▼
[Search]  SEARCH_PREVIEW(query="PPE Solvent Grade 41", filter=CATEGORY=safety, limit=1)
          → returns: PAGE_ID='solvent-grade-41-safety'
                     CONTENT_MD="## Solvent Grade 41 Safety
                                 - Wear protective gloves/clothing/eye protection (P280)
                                 - Use only outdoors or in well-ventilated area (P271)
                                 ..."
        │
        ▼
[Return]  No COMPLETE call.
          answer = top_page["CONTENT_MD"]   ← the wiki page IS the answer
          lane_used = "point_lookup"
          duration_ms ≈ 5,000ms
          sources = 1 page
```

**Why this is fast:** The wiki page was already compiled to be a concise, structured summary.
There is no need to call an LLM again — you're reading from a pre-built knowledge base,
exactly like looking something up in Wikipedia.

---

### Lane 2: synthesis

**When to use:** The answer requires combining facts from multiple wiki pages.
No single page has the complete answer.

**Example question:** `"Which production lines have both overdue maintenance AND Cpk below 1.33?"`

This crosses two categories — maintenance (overdue tasks) and qc (Cpk values).
No single wiki page contains both facts for the same line.

```
ANSWER_QUESTION called
        │
        ▼
[Classify] claude-sonnet-4-5 sees: "...both overdue maintenance AND Cpk below 1.33?"
           → returns: "synthesis"
           → category: "maintenance"  (best single hint the classifier can give)
        │
        ▼
[Search]  SEARCH_PREVIEW(query=..., filter=CATEGORY=maintenance, limit=8)
          → returns 8 maintenance pages:
              maintenance-schedule-l2  (ALERT: 3 overdue)
              maintenance-schedule-l3  (ALERT: 3 overdue, T124478, T302790, T834820)
              maintenance-schedule-l6  (ALERT: 9 overdue)
              maintenance-schedule-l10 (ALERT: 5 overdue)
              pm-schedule-l4           (ALERT: T736188 M072, T835360 M059)
              ...
        │
        ▼
[Synthesise]  claude-sonnet-4-5 receives ALL 8 pages as context:
              "You are a manufacturing expert. Answer using ONLY the wiki context.
               ...
               WIKI CONTEXT:
               ### Maintenance Schedule L3
               - ALERT: Tasks overdue: T124478, T302790, T834820
               ...
               ### Maintenance Schedule L6
               - ALERT: 9 overdue tasks
               ..."

              → Answer: "Lines L2, L3, L4, L6, L8, L10 all have overdue tasks.
                          Cpk data not available in the maintenance context — QC pages
                          needed to complete the cross-document answer."
        │
        ▼
[Return]  lane_used = "synthesis"
          duration_ms ≈ 12,000ms
          sources = 8 pages
```

**Note on the cross-category case:** When a synthesis question spans two categories
(maintenance + qc), the classifier picks the dominant one. A future improvement is to
detect the question spans multiple categories and drop the filter, pulling from both.

---

## 7. How Files and Tables Talk to Each Other (Relationships)

There are three kinds of relationships in this system:

### 7.1 Hard foreign keys (DOC_ID → WIKI_PAGES.SOURCE_DOCS)

`RAW_DOCUMENTS.DOC_ID` is recorded in `WIKI_PAGES.SOURCE_DOCS` (an ARRAY column) when a
wiki page is compiled. This tracks provenance — which PDFs produced which wiki pages.

```sql
-- "Which wiki pages came from equipment_spec_0002?"
SELECT PAGE_ID, PAGE_TITLE
FROM WIKI_PAGES
WHERE ARRAY_CONTAINS('equipment_spec_0002'::VARIANT, SOURCE_DOCS);

-- "Which raw documents contributed to page 'equipment-m015-okuma-4372'?"
SELECT VALUE::VARCHAR AS doc_id
FROM WIKI_PAGES, LATERAL FLATTEN(SOURCE_DOCS)
WHERE PAGE_ID = 'equipment-m015-okuma-4372';
```

### 7.2 The WIKI_INDEX join (PAGE_ID = PAGE_ID)

`WIKI_INDEX` is a compact catalog — one row per wiki page with just the summary and
keywords. `WIKI_PAGES` has the full content. They share `PAGE_ID` as a primary key.
The Cortex Search service joins them at index time:

```sql
-- This is the query behind WIKI_SEARCH:
SELECT p.PAGE_ID, p.PAGE_TITLE, p.CATEGORY, p.CONTENT_MD, i.ONE_LINE_SUMMARY
FROM WIKI_PAGES p
JOIN WIKI_INDEX i USING (PAGE_ID);
```

So when you search, you get both the full content (from `WIKI_PAGES`) and the one-liner
summary (from `WIKI_INDEX`) in the same result row.

### 7.3 Soft cross-references in CONTENT_MD (entity linking)

This is the Karpathy insight applied to cross-document relationships. The LLM is instructed
during compilation to embed explicit cross-references in the markdown:

```markdown
## Maintenance Schedule M015

Machine M015 (Okuma-4372) is a punch press on Line L4, Bay-11.
Supplier: Siemens Industry Inc.

→ See: equipment-m015-okuma-4372
→ See: supplier-siemens-industry
→ See: qc-metrics-l4-q2-2025

- ALERT: T736188 — Verify axis backlash — OVERDUE
- ALERT: T835360 — Replace coolant filter — OVERDUE
```

The `→ See: page-id` notation is a soft reference — it is not enforced by a foreign key,
but it means:

1. When the LLM reads a maintenance page during synthesis, it knows which equipment and
   supplier pages are related
2. A future graph-traversal step could follow these references automatically to pull
   related context without needing a new search

These references are defined by the domain schema prompt in `COMPILE_WIKI_PAGE`:

```
CROSS-REFERENCES — always add:
- Maintenance records → the machine they describe
- QC reports → the production line and machines involved
- Supplier pages → every machine they supply
- FMEA entries → the machine and its maintenance history
```

The LLM enforces this consistently because it's in every compilation prompt.

---

## 8. The Full Relationship Map

```
pdf_generators/                     snowflake/01_setup_infra.sql
  generate_all.py                         │
       │                                  ▼
       │  produces                  @MFG_STAGE (internal stage)
       ▼                                  │
  output/*.pdf  ──── snow stage copy ──►  │
                                          │ TO_FILE('@MFG_STAGE', 'file.pdf')
                                          ▼
                              PARSE_NEW_DOCUMENTS  ──► RAW_DOCUMENTS
                              (02_ingest_pipeline.sql     DOC_ID (PK)
                               line 9)                    PLAIN_TEXT
                                          │               DOC_TYPE
                                          │ DOC_ID
                                          ▼
                              COMPILE_WIKI_PAGE    ──► WIKI_PAGES
                              (02_ingest_pipeline.sql     PAGE_ID (PK)
                               line 120)                  CONTENT_MD
                                          │               SOURCE_DOCS ──► [DOC_ID, ...]
                                          │ PAGE_ID
                                          ▼
                                       WIKI_INDEX
                                          PAGE_ID (PK, FK → WIKI_PAGES)
                                          ONE_LINE_SUMMARY
                                          KEYWORDS
                                          │
                                          │ JOIN WIKI_PAGES ON PAGE_ID
                                          ▼
                                    WIKI_SEARCH (Cortex Search Service)
                                    Embeds CONTENT_MD with arctic-embed
                                          │
                                          │ SEARCH_PREVIEW(query, filter, limit)
                                          ▼
                              ANSWER_QUESTION          ──► WIKI_SAVED_ANSWERS
                              (03_query_procedure.sql       CITATIONS ──► [PAGE_ID, ...]
                               line 9)                      LANE_USED
                                    │
                              ┌─────┴──────┐
                              ▼            ▼
                        point_lookup   synthesis
                        Return top     Combine N pages
                        page directly  → COMPLETE
                        (no LLM call)  → structured answer
```

---

## 9. Concrete Lookup: Tracing One Question End to End

**Question:** `"What is the power rating of machine M015?"`

| Step | What happens | File / Table |
|---|---|---|
| Generate | `equipment_spec.py` creates `equipment_spec_0002.pdf` with M015, 38 kW | `pdf_generators/doc_types/equipment_spec.py` |
| Upload | PDF lands in `@MFG_STAGE` | `@MFG_STAGE` |
| Parse | `AI_PARSE_DOCUMENT` extracts text, inserts row `equipment_spec_0002` | `RAW_DOCUMENTS` |
| Compile | `COMPLETE` reads plain text, writes page `equipment-m015-okuma-4372` | `WIKI_PAGES` |
| Index | Cortex Search embeds the page | `WIKI_SEARCH` service |
| Query | `ANSWER_QUESTION` classifies as `point_lookup`, searches, returns page content | `WIKI_SAVED_ANSWERS` |

**Answer returned (no LLM synthesis call):**
```markdown
**Okuma-4372 (M015) Equipment Overview**

- Machine ID: M015 — Punch Press on Line L4, Bay-11
- Power Rating: 38.0 kW (±2%)
- Max Spindle Speed: 9,503 RPM (±50)
- Manufacturer: Okuma America | Supplier: Siemens Industry Inc.
- Install Date: 2019-11-12
```

The answer came from `WIKI_PAGES` row `equipment-m015-okuma-4372`, which was compiled from
`RAW_DOCUMENTS` row `equipment_spec_0002`, which was parsed from `equipment_spec_0002.pdf`.

---

## 10. Why This Beats Naive RAG for This Use Case

| Capability | Naive RAG | This Pattern |
|---|---|---|
| Simple fact lookup | Pays full LLM cost every time | Returns wiki page directly (no LLM) |
| Cross-doc questions | Chunks lack context, entity refs missing | Wiki pages pre-link entities explicitly |
| Structured data (tables) | Tables become garbled pipe strings | `AI_PARSE_DOCUMENT LAYOUT` preserves structure; LLM extracts key values at compile time |
| Audit trail | None | `INGESTION_LOG` records every parse, compile, query |
| Incremental updates | Full re-index needed | `PARSE_NEW_DOCUMENTS` skips already-processed files; `WIKI_PAGES.VERSION` increments on update |
| Cost | LLM on every query | LLM once at ingest; most queries hit Cortex Search only |
