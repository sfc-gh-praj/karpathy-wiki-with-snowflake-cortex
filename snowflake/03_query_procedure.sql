USE DATABASE MANUFACTURING_WIKI;
USE SCHEMA KNOWLEDGE;

-- ============================================================
-- SP: ANSWER_QUESTION
-- Two-lane routing:
--   Lane 1 (point_lookup) — single factual question about one
--     entity. Cortex Search returns the top wiki page directly.
--     No COMPLETE call. Latency ~200ms.
--   Lane 2 (synthesis)    — cross-document question needing
--     multiple pages combined. Cortex Search fetches up to
--     MAX_CONTEXT_PAGES pages, COMPLETE synthesises an answer.
--     Latency ~10-40s.
--
-- Classifier: mistral-large2 decides the lane.
-- SEARCH_PREVIEW: called with a plain VARCHAR JSON string
--   (not PARSE_JSON — that causes a type error at runtime).
-- Params: session.sql(q, params=[...]) throughout — no .bind().
-- Saves result to WIKI_SAVED_ANSWERS using correct column names:
--   ANSWER_MD, WIKI_PAGE_ID, CITATIONS.
-- ============================================================
CREATE OR REPLACE PROCEDURE ANSWER_QUESTION(
  QUESTION       VARCHAR,
  MAX_CONTEXT_PAGES INT DEFAULT 8
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'answer_question'
COMMENT = 'Two-lane Q&A: point_lookup returns Cortex Search top result directly; synthesis combines pages with COMPLETE.'
AS $$
import json
import re
import time

# ---------------------------------------------------------------------------
# Helper: run Cortex Search and return the results list
# SEARCH_PREVIEW requires a plain VARCHAR string — NOT PARSE_JSON(?)
# ---------------------------------------------------------------------------
def cortex_search(session, query: str, category_filter: str, limit: int) -> list:
    search_query = {
        "query": query,
        "columns": ["PAGE_ID", "PAGE_TITLE", "CATEGORY", "CONTENT_MD", "ONE_LINE_SUMMARY"],
        "limit": limit,
    }
    if category_filter:
        search_query["filter"] = {"@eq": {"CATEGORY": category_filter}}

    # Embed JSON as a SQL string literal (escape single quotes)
    search_json = json.dumps(search_query).replace("'", "''")
    row = session.sql(
        f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW("
        f"  'MANUFACTURING_WIKI.KNOWLEDGE.WIKI_SEARCH', '{search_json}') AS results"
    ).collect()[0]["RESULTS"]

    data = json.loads(row) if isinstance(row, str) else row
    pages = data.get("results", [])

    # Retry without category filter if no results
    if not pages and category_filter:
        fallback = {
            "query": query,
            "columns": ["PAGE_ID", "PAGE_TITLE", "CATEGORY", "CONTENT_MD", "ONE_LINE_SUMMARY"],
            "limit": limit,
        }
        fb_json = json.dumps(fallback).replace("'", "''")
        fb_row = session.sql(
            f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW("
            f"  'MANUFACTURING_WIKI.KNOWLEDGE.WIKI_SEARCH', '{fb_json}') AS results"
        ).collect()[0]["RESULTS"]
        fb_data = json.loads(fb_row) if isinstance(fb_row, str) else fb_row
        pages = fb_data.get("results", [])

    return pages


# ---------------------------------------------------------------------------
# Helper: call COMPLETE safely for large prompts via CTE
# Uses max_tokens to avoid truncated responses
# ---------------------------------------------------------------------------
def complete(session, prompt: str, max_tokens: int = 800) -> str:
    raw = session.sql(
        "WITH p AS (SELECT ? AS prompt) "
        "SELECT SNOWFLAKE.CORTEX.COMPLETE("
        "  'claude-sonnet-4-5',"
        "  [{'role': 'user', 'content': p.prompt}],"
        f"  {{'max_tokens': {max_tokens}}}"
        ") AS ans FROM p",
        params=[prompt]
    ).collect()[0]["ANS"]

    # COMPLETE with messages format returns {"choices":[{"messages":"..."}]}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if "choices" in parsed:
                return parsed["choices"][0].get("messages", raw)
        except json.JSONDecodeError:
            pass
    return raw or ""


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------
def answer_question(session, question: str, max_context_pages: int = 8) -> dict:
    t0 = time.time()

    # ------------------------------------------------------------------
    # Step 1: Classify the question → point_lookup or synthesis
    #
    # point_lookup: single entity, single fact, single doc.
    #   "What is the power rating of M015?"
    #   "What PPE does Solvent Grade 41 require?"
    #   "Who is the supplier for the Okuma-4372?"
    #
    # synthesis: cross-document, comparison, correlation, trend.
    #   "Which lines have both overdue maintenance AND Cpk < 1.33?"
    #   "Are there contradictions between SDS and maintenance procedures?"
    #   "Summarise all quality risks on Line L3"
    # ------------------------------------------------------------------
    classify_prompt = (
        "You are a routing classifier for a manufacturing knowledge base.\n"
        "Classify this question as either 'point_lookup' or 'synthesis'.\n\n"
        "point_lookup: asks for ONE specific fact about ONE entity.\n"
        "  Examples: RPM of a specific machine, storage temp of a chemical,\n"
        "  supplier name for a part, maintenance interval for one task.\n\n"
        "synthesis: needs info from MULTIPLE documents, comparisons, trends,\n"
        "  correlations, or a summary across several entities.\n"
        "  Examples: which lines have both maintenance alerts AND quality issues,\n"
        "  contradictions across docs, top risks across all FMEAs.\n\n"
        f"Question: {question}\n\n"
        "Reply with ONLY one word: point_lookup  OR  synthesis"
    )
    classification = complete(session, classify_prompt, max_tokens=10).strip().lower()
    lane = "synthesis" if "synthesis" in classification else "point_lookup"

    # Infer category to narrow the search
    cat_prompt = (
        "Classify into ONE word. "
        "Categories: equipment, maintenance, qc, safety, production, supplier, fmea, general. "
        f"Question: {question}"
    )
    category_raw = complete(session, cat_prompt, max_tokens=10).strip().lower().split()[0]
    valid_cats = {"equipment", "maintenance", "qc", "safety", "production", "supplier", "fmea"}
    category_filter = category_raw if category_raw in valid_cats else None

    # ------------------------------------------------------------------
    # Step 2: Search
    # Lane 1 → fetch only top 1 result (no synthesis needed)
    # Lane 2 → fetch up to max_context_pages
    # ------------------------------------------------------------------
    search_limit = 1 if lane == "point_lookup" else max_context_pages
    # point_lookup: apply category filter for precision
    # synthesis: no category filter — cross-category retrieval is the point
    search_filter = category_filter if lane == "point_lookup" else None
    pages = cortex_search(session, question, search_filter, search_limit)

    if not pages:
        return {
            "answer": "No relevant wiki pages found for this question.",
            "lane_used": lane,
            "sources": [],
            "duration_ms": int((time.time() - t0) * 1000),
        }

    sources = [{"page_id": p.get("PAGE_ID"), "title": p.get("PAGE_TITLE")} for p in pages]

    # ------------------------------------------------------------------
    # Step 3a — LANE 1 (point_lookup)
    # Return the top wiki page content directly. No COMPLETE call.
    # The wiki page was already compiled to be a concise, factual summary.
    # ------------------------------------------------------------------
    if lane == "point_lookup":
        top = pages[0]
        answer = (
            f"**{top.get('PAGE_TITLE', '')}**\n\n"
            f"{top.get('CONTENT_MD', '')}"
        )
        result = {
            "answer": answer,
            "lane_used": "point_lookup",
            "sources": sources,
            "category_filter": category_filter,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Step 3b — LANE 2 (synthesis)
    # Combine multiple wiki pages and ask COMPLETE to synthesise.
    # ------------------------------------------------------------------
    else:
        context = "\n\n".join(
            f"### {p.get('PAGE_TITLE', '')}\n{p.get('CONTENT_MD', '')}"
            for p in pages
        )
        synthesis_prompt = (
            "You are a manufacturing expert. Answer using ONLY the wiki context below.\n"
            "Include equipment IDs (M-numbers, L-numbers), numeric values with units.\n"
            "Highlight any ALERT flags found in the context.\n"
            "If the answer is not in the context, say so clearly.\n"
            "Format as concise, well-structured markdown.\n\n"
            f"QUESTION: {question}\n\n"
            f"WIKI CONTEXT:\n{context[:12000]}"
        )
        answer = complete(session, synthesis_prompt, max_tokens=800)
        result = {
            "answer": answer,
            "lane_used": "synthesis",
            "sources": sources,
            "category_filter": category_filter,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Step 4: Persist to WIKI_SAVED_ANSWERS
    # Columns: ANSWER_MD, WIKI_PAGE_ID, CITATIONS (ARRAY)
    # ------------------------------------------------------------------
    try:
        session.sql(
            "INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.WIKI_SAVED_ANSWERS "
            "(QUESTION, ANSWER_MD, WIKI_PAGE_ID, CITATIONS, LANE_USED) "
            "SELECT ?, ?, ?, PARSE_JSON(?), ?",
            params=[
                question,
                result["answer"],
                sources[0]["page_id"] if sources else None,
                json.dumps([s["page_id"] for s in sources]),
                lane,
            ]
        ).collect()
    except Exception:
        pass

    return result
$$;
