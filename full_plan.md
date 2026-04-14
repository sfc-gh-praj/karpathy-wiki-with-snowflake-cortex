# Proposed plan
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 ## Full Implementation Plan

 Context

 • Python 3.11.5 with Faker, numpy, pandas, matplotlib, Pillow available
 • reportlab needs to be installed (confirmed available via pip)
 • Target: Streamlit in Snowflake (SiS)
 • Existing files: plan.md, scaling-analysis.md

 ────────────────────────────────────────

 Final File Structure

   karpathy-workflow/
     requirements.txt                       ← pip deps (reportlab, faker)

     pdf_generators/
       data_generator.py                    ← shared Faker data factory
                                              (machines M001-M200, lines L1-L10,
                                               suppliers S001-S020, consistent universe)
       doc_types/
         equipment_spec.py                  ← Type 1 (50-60 pages, 80 PDFs)
         maintenance_report.py              ← Type 2 (60-80 pages, 80 PDFs)
         qc_report.py                       ← Type 3 (55-70 pages, 70 PDFs)
         safety_data_sheet.py               ← Type 4 (50-55 pages, 70 PDFs)
         production_log.py                  ← Type 5 (80-100 pages, 70 PDFs)
         parts_catalog.py                   ← Type 6 (70-90 pages, 65 PDFs)
         fmea_worksheet.py                  ← Type 7 (60-75 pages, 65 PDFs)
       generate_all.py                      ← orchestrator with multiprocessing

     pdfs/                                  ← 500 generated PDFs land here

     snowflake/
       01_setup_infra.sql                   ← DB, schema, stage, 4 tables
       02_ingest_pipeline.sql               ← AI_PARSE_DOCUMENT + COMPLETE wiki SP
       03_query_procedure.sql               ← ANSWER_QUESTION SP (two-lane routing)
       04_lint_procedure.sql                ← LINT_WIKI SP

     streamlit/
       app.py                               ← SiS app (4 tabs)
       utils/
         wiki_ops.py                        ← ingest / query / lint wrappers

     diagrams/
       flow_diagram.py                      ← generates static PNG architecture diagram
       animated_flow.py                     ← generates animated GIF (end-to-end flow)

     output/
       architecture.png                     ← static flow diagram
       karpathy_wiki_flow.gif               ← animated end-to-end GIF

 ────────────────────────────────────────

 Implementation Steps

 Step 1 — Install dependencies & generate requirements.txt

   reportlab==4.4.10
   faker (already installed)

 Step 2 — Shared data factory (data_generator.py)

 Single Faker-seeded factory that generates a consistent manufacturing universe reused across all 7 doc types:

 • 200 machines (M001–M200) with model, line, bay, installation date, supplier
 • 10 production lines (L1–L10)
 • 20 suppliers (S001–S020) with lead times, part types
 • 50 chemical/lubricant SKUs
 • 30 technician names + IDs
 • Randomised but deterministic (fixed seed per PDF index) so data is internally consistent per document

 Step 3 — Seven PDF generator modules

 Each module implements one class with a generate(output_path, seed) method using reportlab:

 ┌────────────────────┬────────┬───────┬──────────────────────────────────────────────────────┐
 │ Type               │ Pages  │ Count │ Layout features                                      │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ Equipment Spec     │ 50-60  │ 80    │ Two-column, spec table, matplotlib diagram image     │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ Maintenance Report │ 60-80  │ 80    │ Multi-row header tables, parts log, summary stats    │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ QC Report          │ 55-70  │ 70    │ matplotlib bar chart + SPC chart embedded, KPI boxes │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ Safety Data Sheet  │ 50-55  │ 70    │ GHS 16-section, hazard table, pictogram images       │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ Production Log     │ 80-100 │ 70    │ Wide landscape table, multi-page, shift summaries    │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ Parts Catalog      │ 70-90  │ 65    │ Grid with thumbnail images, pricing table            │
 ├────────────────────┼────────┼───────┼──────────────────────────────────────────────────────┤
 │ FMEA Worksheet     │ 60-75  │ 65    │ Nested header table, RPN scores, action log          │
 └────────────────────┴────────┴───────┴──────────────────────────────────────────────────────┘

 Step 4 — generate_all.py orchestrator

 • Uses multiprocessing.Pool with 8 workers
 • Generates 500 PDFs in parallel into pdfs/
 • Progress bar via tqdm
 • Estimated time: ~5-8 minutes with 8 cores

 Step 5 — Snowflake infrastructure SQL (01_setup_infra.sql)

   -- Database, schema, internal stage
   -- RAW_DOCUMENTS table (DOC_ID, FILE_NAME, STAGE_PATH, PARSED_TEXT VARIANT, PLAIN_TEXT, PAGE_COUNT)
   -- WIKI_PAGES table (PAGE_ID, PAGE_TITLE, CATEGORY, CONTENT_MD, SOURCE_DOCS ARRAY, VERSION)
   -- WIKI_INDEX table (PAGE_ID, PAGE_TITLE, CATEGORY, ONE_LINE_SUMMARY, KEYWORDS ARRAY)
   -- INGESTION_LOG table (LOG_ID, OPERATION, DOC_ID, DETAIL, PERFORMED_AT)

 Step 6 — Ingest pipeline (02_ingest_pipeline.sql)

 Two Snowpark Python stored procedures:

 PARSE_NEW_DOCUMENTS() — scans stage, calls AI_PARSE_DOCUMENT with LAYOUT mode on unprocessed PDFs, inserts into RAW_DOCUMENTS. Skips already-ingested files (incremental safe).

 COMPILE_WIKI(doc_id VARCHAR) — takes one DOC_ID, calls COMPLETE with domain schema prompt + parsed text, produces structured wiki pages, upserts into WIKI_PAGES + WIKI_INDEX, appends to INGESTION_LOG.
Can be called for first load (all docs) or incremental (one new doc).

 The manufacturing domain schema prompt is embedded in this procedure — this is what teaches the LLM what to extract (machines, suppliers, red flags, contradictions, cross-references).

 Step 7 — Query procedure (03_query_procedure.sql)

 ANSWER_QUESTION(question VARCHAR) RETURNS OBJECT

 Two-lane routing:

 1. Classify question with COMPLETE → point_lookup or synthesis
 2. Point lookup lane: Cortex Search over WIKI_PAGES with attribute filter → top 3 pages → COMPLETE → answer
 3. Synthesis lane: Read WIKI_INDEX summary → COMPLETE picks relevant page IDs → fetch pages → COMPLETE synthesises → answer

 Returns: {answer, citations, lane_used, wiki_pages_read, latency_ms}

 Step 8 — Lint procedure (04_lint_procedure.sql)

 LINT_WIKI() RETURNS TEXT — reads all wiki pages, calls COMPLETE to find: orphan pages, contradictions, stale entries, missing cross-references. Returns markdown lint report.

 Step 9 — Streamlit in Snowflake app (streamlit/app.py)

 Tab 1 — Ask

 • Text input + "Ask" button
 • Calls ANSWER_QUESTION SP
 • Renders answer as markdown
 • Shows citations (wiki page titles + source PDFs)
 • Shows which lane was used (point lookup vs synthesis)
 • "Save to Wiki" button

 Tab 2 — Wiki

 • Category filter sidebar
 • Table of all wiki pages from WIKI_INDEX
 • Click a row → renders full CONTENT_MD as st.markdown
 • Shows source PDFs that contributed

 Tab 3 — Ingest

 • Lists PDFs in stage via DIRECTORY(@MFG_STAGE)
 • Checkboxes for selection
 • "Ingest Selected" → calls PARSE_NEW_DOCUMENTS then COMPILE_WIKI per doc
 • st.progress bar
 • Live tail of INGESTION_LOG

 Tab 4 — Wiki Health

 • "Run Lint" button → calls LINT_WIKI
 • Renders lint report as markdown
 • Shows stats: total pages, pages per category, last updated

 Step 10 — Static flow diagram (diagrams/flow_diagram.py)

 matplotlib figure with 3 sections:

 1. System architecture: PDF stage → AI_PARSE_DOCUMENT → RAW_DOCUMENTS → COMPLETE → WIKI_PAGES → WIKI_INDEX → Query → Answer
 2. First load flow: all PDFs processed, full wiki built
 3. Incremental load flow: new PDF only, delta wiki update

 Saved as output/architecture.png

 Step 11 — Animated GIF (diagrams/animated_flow.py)

 matplotlib FuncAnimation → Pillow PillowWriter → output/karpathy_wiki_flow.gif

 ~90 frames at 12fps = ~7.5 second loop, showing 5 scenes:

 ┌────────────────────────────┬────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ Scene                      │ Frames │ What animates                                                                                              │
 ├────────────────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 1. PDFs in stage           │ 1-15   │ 500 PDF boxes appear in a grid, labelled by type                                                           │
 ├────────────────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 2. First load — parse      │ 16-35  │ Scanning arrow moves across PDFs, RAW_DOCUMENTS table rows fill up                                         │
 ├────────────────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 3. First load — wiki build │ 36-55  │ COMPLETE icon processes docs, wiki pages fly into WIKI_PAGES table, index builds                           │
 ├────────────────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 4. Query flow              │ 56-72  │ Question bubble → index lookup (pages highlight) → COMPLETE → answer appears                               │
 ├────────────────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ 5. Incremental load        │ 73-90  │ Single new PDF drops in, only that file scanned, only affected wiki pages flash/update, "delta only" label │
 └────────────────────────────┴────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ────────────────────────────────────────

 Verification Steps

 1. Run generate_all.py → confirm 500 PDFs in pdfs/, check random sample opens correctly
 2. Run 01_setup_infra.sql → SHOW TABLES confirms 4 tables
 3. Upload 5 sample PDFs → run PARSE_NEW_DOCUMENTS() → check RAW_DOCUMENTS has 5 rows
 4. Run COMPILE_WIKI(doc_id) on 2 docs → check WIKI_PAGES and WIKI_INDEX populated
 5. Run ANSWER_QUESTION('What machines are on Line 4?') → verify answer + citations returned
 6. Add 1 new PDF → re-run ingest → verify only the new doc appears in INGESTION_LOG
 7. Open animated GIF → verify all 5 scenes play correctly

 ────────────────────────────────────────

 Critical Files

 • pdf_generators/data_generator.py — shared data factory, seeds consistency across all 500 PDFs
 • pdf_generators/generate_all.py — orchestrates all 7 types with multiprocessing
 • snowflake/02_ingest_pipeline.sql — core of the system: AI_PARSE_DOCUMENT + COMPLETE + domain schema prompt
 • snowflake/03_query_procedure.sql — two-lane query routing logic
 • diagrams/animated_flow.py — end-to-end animated GIF showing the full Karpathy pattern