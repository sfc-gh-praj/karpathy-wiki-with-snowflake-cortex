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
  QUESTION          VARCHAR,
  MAX_CONTEXT_PAGES INT DEFAULT 8,
  PERIOD            VARCHAR DEFAULT NULL
)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'answer_question'
COMMENT = 'Two-lane Q/A: point_lookup returns Cortex Search top result directly; synthesis combines pages with COMPLETE.'
AS $$
import json
import re
import time

# ---------------------------------------------------------------------------
# Helper: run Cortex Search and return the results list
# SEARCH_PREVIEW requires a plain VARCHAR string — NOT PARSE_JSON(?)
# ---------------------------------------------------------------------------
def cortex_search(session, query: str, category_filter: str, limit: int, period: str = None) -> list:
    search_query = {
        "query": query,
        "columns": ["PAGE_ID", "PAGE_TITLE", "CATEGORY", "CONTENT_MD", "ONE_LINE_SUMMARY", "PERIOD_LABEL"],
        "limit": limit,
    }
    # Build filter: combine category + period when both provided
    filters = []
    if category_filter:
        filters.append({"@eq": {"CATEGORY": category_filter}})
    if period:
        filters.append({"@eq": {"PERIOD_LABEL": period}})
    if len(filters) == 2:
        search_query["filter"] = {"@and": filters}
    elif len(filters) == 1:
        search_query["filter"] = filters[0]

    # Embed JSON as a SQL string literal (escape single quotes)
    search_json = json.dumps(search_query).replace("'", "''")
    row = session.sql(
        f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW("
        f"  'MANUFACTURING_WIKI.KNOWLEDGE.WIKI_SEARCH', '{search_json}') AS results"
    ).collect()[0]["RESULTS"]

    data = json.loads(row) if isinstance(row, str) else row
    pages = data.get("results", [])

    # Retry without category filter if no results (keep period filter if set)
    if not pages and category_filter:
        fallback = {
            "query": query,
            "columns": ["PAGE_ID", "PAGE_TITLE", "CATEGORY", "CONTENT_MD", "ONE_LINE_SUMMARY", "PERIOD_LABEL"],
            "limit": limit,
        }
        if period:
            fallback["filter"] = {"@eq": {"PERIOD_LABEL": period}}
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
# Helper: find the best-matching paragraph in a block of raw text
# Scores paragraphs by keyword density, returns sentence-boundary cut
# ---------------------------------------------------------------------------
def _extract_paragraph(text: str, kw_lower: list, max_len: int = 400) -> str:
    # Pre-process: remove lines that are running headers or section headings,
    # which otherwise score artificially high against wiki page title keywords.
    # (1) All-caps identifier lines: "PRODUCTION LOG — PL-L9-2025-07-01"
    #     str.isupper() is True when every cased char is uppercase — digits/hyphens are fine
    # (2) Numbered section headings: "1. Week Summary", "2. Daily Breakdown"
    clean_lines = []
    for line in text.splitlines():
        s = line.strip()
        if s and s.isupper():
            continue  # all-caps running header
        if s and re.match(r'^\d+\.\s+\S', s) and '|' not in s and len(s) < 60:
            continue  # numbered section heading
        clean_lines.append(line)
    text = '\n'.join(clean_lines)

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text)
                  if p.strip() and not p.strip().startswith('#')]
    if not paragraphs:
        return text.strip()[:max_len]
    best = paragraphs[0]
    best_score = 0
    for para in paragraphs:
        score = sum(1 for kw in kw_lower if kw in para.lower())
        # On equal score prefer the longer (data-richer) paragraph — tables beat headings
        if score > best_score or (score == best_score and len(para) > len(best)):
            best_score = score
            best = para
    if len(best) <= max_len:
        return best
    cut = best.rfind('. ', 0, max_len)
    if cut > max_len // 2:
        return best[:cut + 1]
    return best[:max_len] + "\u2026"


# ---------------------------------------------------------------------------
# Helper: locate the best PDF page and raw excerpt for a wiki page title
# Splits PLAIN_TEXT by "\nPage N\n" markers, scores pages by keyword density
# Returns (page_label, raw_excerpt) e.g. ("Page 5", "| Power: | 45 kW |...")
# Falls back gracefully when no page markers exist in the document
# ---------------------------------------------------------------------------
def _find_raw_location(raw_text: str, title: str, max_excerpt: int = 400) -> tuple:
    if not raw_text:
        return "", ""
    stopwords = {"the", "and", "for", "with", "from", "this", "that", "are",
                 "has", "its", "of", "in", "a", "an", "is", "to", "at", "on"}
    kw_lower = [w.lower() for w in re.findall(r'\b\w+\b', title)
                if len(w) >= 2 and w.lower() not in stopwords]
    # Split raw text into pages using embedded "Page N" markers
    parts = re.split(r'\nPage\s+(\d+)\s*\n', raw_text)
    # parts: [pre_text, "1", page1_text, "2", page2_text, ...]
    if len(parts) < 3:
        # No page markers — search the full text without a page label
        return "", _extract_paragraph(raw_text, kw_lower, max_excerpt)
    segments = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            segments.append((parts[i], parts[i + 1]))
    best_page, best_text = segments[0]
    best_score = 0
    for pnum, ptext in segments:
        score = sum(1 for kw in kw_lower if kw in ptext.lower())
        if score > best_score:
            best_score = score
            best_page = pnum
            best_text = ptext
    return f"Page {best_page}", _extract_paragraph(best_text, kw_lower, max_excerpt)


# ---------------------------------------------------------------------------
# Helper: extract a readable snippet from wiki CONTENT_MD
# Skips header lines, returns first substantive paragraph up to max_len chars
# ---------------------------------------------------------------------------
def _snippet(text: str, max_len: int = 400) -> str:
    if not text:
        return ""
    lines = text.strip().splitlines()
    content_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            content_lines.append(stripped)
            if sum(len(l) for l in content_lines) >= max_len:
                break
    body = '\n'.join(content_lines).strip() or text.strip()
    if len(body) <= max_len:
        return body
    cut = body.rfind('. ', 0, max_len)
    if cut > max_len // 2:
        return body[:cut + 1]
    return body[:max_len] + "…"


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------
def answer_question(session, question: str, max_context_pages: int = 8, period: str = None) -> dict:
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
    pages = cortex_search(session, question, search_filter, search_limit, period)

    if not pages:
        return {
            "answer": "No relevant wiki pages found for this question.",
            "lane_used": lane,
            "sources": [],
            "duration_ms": int((time.time() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Batch-fetch raw PDF text for all source wiki pages in one JOIN query.
    # WIKI_PAGES.SOURCE_DOCS is a VARIANT array of doc_ids; LATERAL FLATTEN
    # unnests it so we can join to RAW_DOCUMENTS.PLAIN_TEXT.
    # page_raw_text: {page_id -> plain_text_string}
    # ------------------------------------------------------------------
    safe_ids = ", ".join(
        f"'{p.get('PAGE_ID', '').replace(chr(39), chr(39)*2)}'"
        for p in pages
    )
    try:
        raw_rows = session.sql(
            "SELECT wp.PAGE_ID, rd.PLAIN_TEXT "
            "FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES wp, "
            "LATERAL FLATTEN(input => wp.SOURCE_DOCS) f "
            "JOIN MANUFACTURING_WIKI.KNOWLEDGE.RAW_DOCUMENTS rd "
            "  ON rd.DOC_ID = f.value::VARCHAR "
            f"WHERE wp.PAGE_ID IN ({safe_ids})"
        ).collect()
        page_raw_text = {r["PAGE_ID"]: (r["PLAIN_TEXT"] or "") for r in raw_rows}
    except Exception:
        page_raw_text = {}

    sources = []
    for p in pages:
        pid = p.get("PAGE_ID")
        raw = page_raw_text.get(pid, "")
        page_label, raw_excerpt = _find_raw_location(raw, p.get("PAGE_TITLE", ""))
        sources.append({
            "page_id": pid,
            "title": p.get("PAGE_TITLE"),
            "category": p.get("CATEGORY", ""),
            # raw_excerpt is actual PDF text; fall back to wiki snippet if unavailable
            "snippet": raw_excerpt or _snippet(p.get("CONTENT_MD", "")),
            "page_label": page_label,   # e.g. "Page 5" or "" if no markers found
        })

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
            "period_used": period,
            "context_truncated": False,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Step 3b — LANE 2 (synthesis)
    # Combine multiple wiki pages and ask COMPLETE to synthesise.
    # Equal-budget distribution: each page gets MAX_CONTEXT_CHARS / N chars,
    # so no single page dominates and no page is silently dropped entirely.
    # ------------------------------------------------------------------
    else:
        MAX_CONTEXT_CHARS = 50000   # ~12.5k tokens, well within claude-sonnet-4-5 200k limit
        per_page_budget = MAX_CONTEXT_CHARS // max(len(pages), 1)
        context_parts = []
        any_truncated = False
        for p in pages:
            content = f"### {p.get('PAGE_TITLE', '')}\n{p.get('CONTENT_MD', '')}"
            if len(content) > per_page_budget:
                content = content[:per_page_budget] + "\n[... content truncated]"
                any_truncated = True
            context_parts.append(content)
        context = "\n\n".join(context_parts)
        synthesis_prompt = (
            "You are a manufacturing expert. Answer using ONLY the wiki context below.\n"
            "Include equipment IDs (M-numbers, L-numbers), numeric values with units.\n"
            "Highlight any ALERT flags found in the context.\n"
            "If the answer is not in the context, say so clearly.\n"
            "Format as concise, well-structured markdown.\n\n"
            f"QUESTION: {question}\n\n"
            f"WIKI CONTEXT:\n{context}"
        )
        answer = complete(session, synthesis_prompt, max_tokens=800)
        result = {
            "answer": answer,
            "lane_used": "synthesis",
            "sources": sources,
            "category_filter": category_filter,
            "period_used": period,
            "context_truncated": any_truncated,
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
