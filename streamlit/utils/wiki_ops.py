"""Helper functions for Manufacturing Wiki operations via Snowpark."""

import json
from snowflake.snowpark import Session

SCHEMA = "MANUFACTURING_WIKI.KNOWLEDGE"


def get_stage_files(session: Session) -> list[dict]:
    """Return all PDFs listed in @MFG_STAGE."""
    rows = session.sql(
        f"SELECT RELATIVE_PATH, SIZE, LAST_MODIFIED"
        f" FROM DIRECTORY(@{SCHEMA}.MFG_STAGE)"
        f" WHERE RELATIVE_PATH LIKE '%.pdf'"
        f" ORDER BY RELATIVE_PATH"
    ).collect()
    return [row.as_dict() for row in rows]


def get_ingested_docs(session: Session) -> list[dict]:
    """Return all documents that have been parsed and stored in RAW_DOCUMENTS."""
    rows = session.sql(
        f"SELECT DOC_ID, FILE_NAME, DOC_TYPE, PAGE_COUNT, INGESTED_AT"
        f" FROM {SCHEMA}.RAW_DOCUMENTS"
    ).collect()
    return [row.as_dict() for row in rows]


def get_wiki_index(session: Session, category_filter: str = None) -> list[dict]:
    """Return WIKI_INDEX rows, optionally filtered by category."""
    if category_filter and category_filter.lower() != "all":
        rows = session.sql(
            f"SELECT * FROM {SCHEMA}.WIKI_INDEX"
            f" WHERE CATEGORY = ?"
            f" ORDER BY CATEGORY, PAGE_TITLE",
            params=[category_filter],
        ).collect()
    else:
        rows = session.sql(
            f"SELECT * FROM {SCHEMA}.WIKI_INDEX ORDER BY CATEGORY, PAGE_TITLE"
        ).collect()
    return [row.as_dict() for row in rows]


def get_wiki_page(session: Session, page_id: str) -> dict:
    """Return the full WIKI_PAGES row for a given page_id."""
    rows = session.sql(
        f"SELECT * FROM {SCHEMA}.WIKI_PAGES WHERE PAGE_ID = ?",
        params=[page_id],
    ).collect()
    return rows[0].as_dict() if rows else {}


def ingest_document(session: Session, file_name: str) -> dict:
    """Parse new documents then compile the wiki page for file_name."""
    parse_rows = session.sql(
        f"CALL {SCHEMA}.PARSE_NEW_DOCUMENTS(50)"
    ).collect()

    # Find the doc_id that was just created for this file
    doc_rows = session.sql(
        f"SELECT DOC_ID FROM {SCHEMA}.RAW_DOCUMENTS"
        f" WHERE FILE_NAME = ?"
        f" ORDER BY INGESTED_AT DESC LIMIT 1",
        params=[file_name],
    ).collect()

    result: dict = {"parse": parse_rows[0].as_dict() if parse_rows else {}}

    if doc_rows:
        doc_id = str(doc_rows[0]["DOC_ID"])
        escaped_doc_id = doc_id.replace("'", "''")
        compile_rows = session.sql(
            f"CALL {SCHEMA}.COMPILE_WIKI_PAGE('{escaped_doc_id}')"
        ).collect()
        result["compile"] = compile_rows[0].as_dict() if compile_rows else {}
        result["doc_id"] = doc_id

    return result


def ingest_all_new(session: Session, limit: int = 20) -> dict:
    """Call INGEST_ALL_NEW to parse and compile in one shot."""
    rows = session.sql(
        f"CALL {SCHEMA}.INGEST_ALL_NEW({int(limit)})"
    ).collect()
    if not rows:
        return {}
    raw = rows[0][0]
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {"message": raw}
    return raw if isinstance(raw, dict) else {}


def answer_question(session: Session, question: str, save_to_wiki: bool = False) -> dict:
    """Call ANSWER_QUESTION and return the parsed JSON response dict."""
    escaped = question.replace("'", "''")
    rows = session.sql(
        f"CALL {SCHEMA}.ANSWER_QUESTION('{escaped}')"
    ).collect()
    if not rows:
        return {}
    raw = rows[0][0]
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {"answer": raw}
    return raw if isinstance(raw, dict) else {}


def get_source_pdfs(session: Session, page_ids: list[str]) -> dict[str, list[str]]:
    """Return a mapping of page_id -> [pdf_filenames] for the given page IDs."""
    if not page_ids:
        return {}
    placeholders = ", ".join(f"'{pid.replace(chr(39), chr(39)*2)}'" for pid in page_ids)
    rows = session.sql(
        f"""
        SELECT wp.PAGE_ID, rd.FILE_NAME
        FROM {SCHEMA}.WIKI_PAGES wp,
        LATERAL FLATTEN(input => wp.SOURCE_DOCS) f
        JOIN {SCHEMA}.RAW_DOCUMENTS rd ON rd.DOC_ID = f.value::VARCHAR
        WHERE wp.PAGE_ID IN ({placeholders})
        ORDER BY wp.PAGE_ID, rd.FILE_NAME
        """
    ).collect()
    result: dict[str, list[str]] = {}
    for row in rows:
        pid = row["PAGE_ID"]
        fname = row["FILE_NAME"]
        result.setdefault(pid, [])
        if fname not in result[pid]:
            result[pid].append(fname)
    return result


def run_lint(session: Session) -> str:
    """Call LINT_WIKI() and return the markdown health report string."""
    rows = session.sql(f"CALL {SCHEMA}.LINT_WIKI()").collect()
    if not rows:
        return ""
    raw = rows[0][0]
    return str(raw) if raw is not None else ""


def get_ingestion_log(session: Session, limit: int = 50) -> list[dict]:
    """Return the most recent ingestion log entries."""
    rows = session.sql(
        f"SELECT LOG_ID, OPERATION, DOC_ID, DETAIL, STATUS, DURATION_MS, PERFORMED_AT"
        f" FROM {SCHEMA}.INGESTION_LOG"
        f" ORDER BY PERFORMED_AT DESC"
        f" LIMIT {int(limit)}"
    ).collect()
    return [row.as_dict() for row in rows]


def get_wiki_stats(session: Session) -> dict:
    """Return aggregate stats: total_pages, pages_by_category, total_docs, last_updated."""
    pages = session.sql(
        f"SELECT COUNT(*) AS TOTAL_PAGES, MAX(UPDATED_AT) AS LAST_UPDATED"
        f" FROM {SCHEMA}.WIKI_INDEX"
    ).collect()
    cats = session.sql(
        f"SELECT CATEGORY, COUNT(*) AS CNT"
        f" FROM {SCHEMA}.WIKI_INDEX"
        f" GROUP BY CATEGORY ORDER BY CNT DESC"
    ).collect()
    docs = session.sql(
        f"SELECT COUNT(*) AS TOTAL_DOCS FROM {SCHEMA}.RAW_DOCUMENTS"
    ).collect()

    return {
        "total_pages": int(pages[0]["TOTAL_PAGES"]) if pages else 0,
        "pages_by_category": {r["CATEGORY"]: int(r["CNT"]) for r in cats},
        "total_docs": int(docs[0]["TOTAL_DOCS"]) if docs else 0,
        "last_updated": pages[0]["LAST_UPDATED"] if pages else None,
    }
