USE DATABASE MANUFACTURING_WIKI;
USE SCHEMA KNOWLEDGE;

-- ============================================================
-- SP 1: PARSE_NEW_DOCUMENTS
-- Scans @MFG_STAGE, calls AI_PARSE_DOCUMENT on unprocessed PDFs.
-- Incremental: skips files already in RAW_DOCUMENTS.
--
-- Key notes:
--   AI_PARSE_DOCUMENT requires TO_FILE('@stage', 'path') to get a
--   proper FILE type. @stage+path as separate args and
--   BUILD_SCOPED_FILE_URL both fail (wrong argument types).
--
--   All parameterised SQL uses session.sql(q, params=[...]).
--   DataFrame has no .bind() method in Snowpark Python.
-- ============================================================
CREATE OR REPLACE PROCEDURE PARSE_NEW_DOCUMENTS(
  MAX_FILES INT DEFAULT 50
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'parse_new_documents'
COMMENT = 'Parses new PDFs from @MFG_STAGE using AI_PARSE_DOCUMENT. Incremental — skips already-processed files.'
AS $$
import json
import re
import time

def parse_new_documents(session, max_files: int = 50) -> dict:
    results = {"processed": 0, "skipped": 0, "errors": 0, "files": []}
    start_time = time.time()

    # Files already ingested
    existing = session.sql(
        "SELECT FILE_NAME FROM MANUFACTURING_WIKI.KNOWLEDGE.RAW_DOCUMENTS"
    ).collect()
    existing_files = {row["FILE_NAME"] for row in existing}

    # All PDFs in stage
    stage_files = session.sql(
        "SELECT RELATIVE_PATH, SIZE FROM DIRECTORY(@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE) "
        "WHERE RELATIVE_PATH LIKE '%.pdf' ORDER BY RELATIVE_PATH"
    ).collect()

    new_files = [f for f in stage_files if f["RELATIVE_PATH"] not in existing_files]
    new_files = new_files[:max_files]

    for file_row in new_files:
        rel_path = file_row["RELATIVE_PATH"]
        doc_id = re.sub(r"[^a-zA-Z0-9_]", "_", rel_path.replace(".pdf", ""))

        fname_lower = rel_path.lower()
        if "equipment" in fname_lower or "spec" in fname_lower:
            doc_type = "equipment_spec"
        elif "maintenance" in fname_lower:
            doc_type = "maintenance"
        elif "qc" in fname_lower or "quality" in fname_lower:
            doc_type = "qc"
        elif "sds" in fname_lower or "safety" in fname_lower:
            doc_type = "sds"
        elif "production" in fname_lower or "log" in fname_lower:
            doc_type = "production"
        elif "catalog" in fname_lower or "parts" in fname_lower:
            doc_type = "catalog"
        elif "fmea" in fname_lower:
            doc_type = "fmea"
        else:
            doc_type = "general"

        t0 = time.time()
        try:
            # TO_FILE() creates a proper FILE type reference for AI_PARSE_DOCUMENT.
            # BUILD_SCOPED_FILE_URL returns VARCHAR which causes a type error.
            parse_result = session.sql(f"""
                SELECT SNOWFLAKE.CORTEX.AI_PARSE_DOCUMENT(
                    TO_FILE('@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE', '{rel_path}'),
                    {{'mode': 'LAYOUT'}}
                ) AS parsed
            """).collect()[0]["PARSED"]

            parsed_json = json.loads(parse_result) if isinstance(parse_result, str) else parse_result
            plain_text = parsed_json.get("content", "")
            page_count = parsed_json.get("numPages", 0)

            session.sql(
                "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.RAW_DOCUMENTS "
                "(DOC_ID, FILE_NAME, STAGE_PATH, PARSED_TEXT, PLAIN_TEXT, PAGE_COUNT, DOC_TYPE) "
                "SELECT ?, ?, ?, PARSE_JSON(?), ?, ?, ?",
                params=[
                    doc_id, rel_path,
                    f"@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE/{rel_path}",
                    json.dumps(parsed_json), plain_text, page_count, doc_type
                ]
            ).collect()

            duration_ms = int((time.time() - t0) * 1000)
            session.sql(
                "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.INGESTION_LOG "
                "(OPERATION, DOC_ID, DETAIL, STATUS, DURATION_MS) "
                "VALUES (?, ?, ?, 'success', ?)",
                params=["ingest", doc_id, f"Parsed {page_count} pages from {rel_path}", duration_ms]
            ).collect()

            results["processed"] += 1
            results["files"].append({"doc_id": doc_id, "pages": page_count, "type": doc_type})

        except Exception as e:
            try:
                session.sql(
                    "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.INGESTION_LOG "
                    "(OPERATION, DOC_ID, DETAIL, STATUS) VALUES (?, ?, ?, 'error')",
                    params=["ingest", doc_id, str(e)[:500]]
                ).collect()
            except Exception:
                pass
            results["errors"] += 1

    results["skipped"] = len(existing_files)
    results["total_duration_s"] = round(time.time() - start_time, 2)
    return results
$$;


-- ============================================================
-- SP 2: COMPILE_WIKI_PAGE
-- Takes one DOC_ID from RAW_DOCUMENTS, calls COMPLETE to build
-- structured wiki pages, upserts into WIKI_PAGES and WIKI_INDEX.
--
-- Key notes:
--   Large prompt passed via CTE (WITH p AS (SELECT ? AS prompt))
--   to avoid Snowpark parameter size limits.
--   max_tokens: 1500 prevents truncated JSON responses.
--   claude-sonnet-4-5 is the model (mistral-large2 was a fallback
--   when claude was unavailable; claude-sonnet-4-5 is now confirmed
--   available in this account).
-- ============================================================
CREATE OR REPLACE PROCEDURE COMPILE_WIKI_PAGE(
  DOC_ID VARCHAR
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'compile_wiki_page'
COMMENT = 'Compiles wiki pages from a parsed document using claude-sonnet-4-5. Updates WIKI_PAGES and WIKI_INDEX.'
AS $$
import json
import re
import time

# SYSTEM_PROMPT is no longer hardcoded here.
# It is loaded at runtime from MANUFACTURING_WIKI.KNOWLEDGE.PROMPT_REGISTRY
# WHERE PROMPT_NAME = 'wiki_compiler' AND IS_ACTIVE = TRUE.
# To change the prompt, INSERT a new row with IS_ACTIVE = TRUE and set the
# old row to IS_ACTIVE = FALSE — no SP redeployment needed.


def extract_json(text: str) -> dict:
    """Robustly extract the outermost JSON object, handling markdown code fences."""
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find('{')
    if start == -1:
        raise ValueError(f"No JSON object found. Response: {cleaned[:200]}")
    depth = 0
    for i, ch in enumerate(cleaned[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise ValueError(f"Truncated JSON (len={len(cleaned)}). Tail: {cleaned[-100:]}")


def compile_wiki_page(session, doc_id: str) -> dict:
    results = {"doc_id": doc_id, "pages_created": 0, "pages_updated": 0, "errors": []}
    t0 = time.time()

    # ------------------------------------------------------------------
    # Load active prompt from PROMPT_REGISTRY.
    # This decouples prompt content from SP code — update the prompt by
    # inserting a new row with IS_ACTIVE=TRUE (and deactivating the old
    # one), no SP redeployment needed.
    # ------------------------------------------------------------------
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
    prompt_id = prompt_rows[0]["PROMPT_ID"]

    rows = session.sql(
        "SELECT PLAIN_TEXT, DOC_TYPE, FILE_NAME "
        "FROM MANUFACTURING_WIKI.KNOWLEDGE.RAW_DOCUMENTS WHERE DOC_ID = ?",
        params=[doc_id]
    ).collect()

    if not rows:
        return {"error": f"DOC_ID {doc_id} not found in RAW_DOCUMENTS"}

    plain_text = (rows[0]["PLAIN_TEXT"] or "")[:15000]
    doc_type = rows[0]["DOC_TYPE"]
    file_name = rows[0]["FILE_NAME"]

    full_prompt = f"{system_prompt}\n\nDoc type: {doc_type} | Source: {file_name}\n\n{plain_text}"

    try:
        # CTE passes the large prompt safely without escaping issues.
        # max_tokens caps output so JSON is never truncated.
        response = session.sql(
            "WITH p AS (SELECT ? AS prompt) "
            "SELECT SNOWFLAKE.CORTEX.COMPLETE("
            "  'claude-sonnet-4-5',"
            "  [{'role': 'user', 'content': p.prompt}],"
            "  {'max_tokens': 1500}"
            ") AS wiki_json FROM p",
            params=[full_prompt]
        ).collect()[0]["WIKI_JSON"]

        # COMPLETE with messages format wraps text in {"choices":[{"messages":"..."}]}
        if isinstance(response, str):
            try:
                resp_obj = json.loads(response)
                if "choices" in resp_obj:
                    response = resp_obj["choices"][0].get("messages", response)
            except json.JSONDecodeError:
                pass

        wiki_data = extract_json(response)
        pages = wiki_data.get("wiki_pages", [])

        for page in pages:
            page_id = re.sub(r'[^a-z0-9-]', '-', page.get("page_id", "").lower().strip())
            page_id = re.sub(r'-+', '-', page_id).strip('-')
            if not page_id:
                continue

            existing = session.sql(
                "SELECT PAGE_ID, VERSION FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES "
                "WHERE PAGE_ID = ?",
                params=[page_id]
            ).collect()

            content_md = page.get("content_md", "")

            if existing:
                version = existing[0]["VERSION"] + 1
                session.sql(
                    "UPDATE MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES "
                    "SET CONTENT_MD = ?, SOURCE_DOCS = ARRAY_APPEND(SOURCE_DOCS, ?), "
                    "VERSION = ?, PROMPT_ID = ?, UPDATED_AT = CURRENT_TIMESTAMP() WHERE PAGE_ID = ?",
                    params=[content_md, doc_id, version, prompt_id, page_id]
                ).collect()
                results["pages_updated"] += 1
            else:
                session.sql(
                    "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES "
                    "(PAGE_ID, PAGE_TITLE, CATEGORY, CONTENT_MD, SOURCE_DOCS, VERSION, PROMPT_ID) "
                    "SELECT ?, ?, ?, ?, ARRAY_CONSTRUCT(?), 1, ?",
                    params=[
                        page_id, page.get("page_title", page_id),
                        page.get("category", "general"), content_md, doc_id, prompt_id
                    ]
                ).collect()
                results["pages_created"] += 1

            session.sql(
                "MERGE INTO MANUFACTURING_WIKI.KNOWLEDGE.WIKI_INDEX AS t "
                "USING (SELECT ? AS page_id, ? AS page_title, ? AS category, "
                "       ? AS one_line_summary, PARSE_JSON(?) AS keywords) AS s "
                "ON t.PAGE_ID = s.page_id "
                "WHEN MATCHED THEN UPDATE SET "
                "    t.ONE_LINE_SUMMARY = s.one_line_summary, "
                "    t.KEYWORDS = s.keywords, "
                "    t.SOURCE_DOC_COUNT = t.SOURCE_DOC_COUNT + 1, "
                "    t.UPDATED_AT = CURRENT_TIMESTAMP() "
                "WHEN NOT MATCHED THEN INSERT "
                "    (PAGE_ID, PAGE_TITLE, CATEGORY, ONE_LINE_SUMMARY, KEYWORDS, SOURCE_DOC_COUNT) "
                "    VALUES (s.page_id, s.page_title, s.category, s.one_line_summary, s.keywords, 1)",
                params=[
                    page_id, page.get("page_title", page_id),
                    page.get("category", "general"),
                    page.get("one_line_summary", ""),
                    json.dumps(page.get("keywords", []))
                ]
            ).collect()

        duration_ms = int((time.time() - t0) * 1000)
        session.sql(
            "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.INGESTION_LOG "
            "(OPERATION, DOC_ID, DETAIL, STATUS, DURATION_MS) VALUES (?, ?, ?, 'success', ?)",
            params=["wiki_compile", doc_id,
                    f"Created {results['pages_created']} pages, updated {results['pages_updated']}",
                    duration_ms]
        ).collect()

    except Exception as e:
        results["errors"].append(str(e))
        try:
            session.sql(
                "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.INGESTION_LOG "
                "(OPERATION, DOC_ID, DETAIL, STATUS) VALUES (?, ?, ?, 'error')",
                params=["wiki_compile", doc_id, str(e)[:500]]
            ).collect()
        except Exception:
            pass

    return results
$$;


-- ============================================================
-- SP 3: INGEST_ALL_NEW
-- Convenience wrapper: parse all new PDFs then compile wiki
-- pages for each one in sequence.
-- ============================================================
CREATE OR REPLACE PROCEDURE INGEST_ALL_NEW(
  MAX_FILES INT DEFAULT 20
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'ingest_all_new'
AS $$
import json

def ingest_all_new(session, max_files: int = 20) -> dict:
    parse_result = session.call("MANUFACTURING_WIKI.KNOWLEDGE.PARSE_NEW_DOCUMENTS", max_files)
    parse_data = json.loads(parse_result) if isinstance(parse_result, str) else parse_result
    processed_files = parse_data.get("files", [])

    wiki_results = []
    for f in processed_files:
        wiki_result = session.call("MANUFACTURING_WIKI.KNOWLEDGE.COMPILE_WIKI_PAGE", f["doc_id"])
        wiki_results.append(wiki_result if isinstance(wiki_result, dict) else json.loads(wiki_result))

    return {
        "parse_summary": parse_data,
        "wiki_compilations": len(wiki_results),
        "total_pages_created": sum(r.get("pages_created", 0) for r in wiki_results)
    }
$$;
