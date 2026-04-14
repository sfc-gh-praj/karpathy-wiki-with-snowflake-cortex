USE DATABASE MANUFACTURING_WIKI;
USE SCHEMA KNOWLEDGE;

-- ============================================================
-- SP: LINT_WIKI
-- Health-checks the wiki for contradictions, orphans, gaps
-- ============================================================
CREATE OR REPLACE PROCEDURE LINT_WIKI()
RETURNS TEXT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'lint_wiki'
COMMENT = 'Reviews wiki for contradictions, orphan pages, stale entries, missing cross-references.'
AS $$
import json
import time

def lint_wiki(session) -> str:
    t0 = time.time()

    # Get all wiki pages summary for lint
    pages = session.sql("""
        SELECT p.PAGE_ID, p.PAGE_TITLE, p.CATEGORY, p.CONTENT_MD,
               p.VERSION, p.UPDATED_AT,
               i.ONE_LINE_SUMMARY, i.SOURCE_DOC_COUNT
        FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES p
        LEFT JOIN MANUFACTURING_WIKI.KNOWLEDGE.WIKI_INDEX i ON p.PAGE_ID = i.PAGE_ID
        ORDER BY p.CATEGORY, p.PAGE_ID
    """).collect()

    total_pages = len(pages)

    # Build a compact representation for the LLM
    pages_summary = []
    for row in pages[:100]:  # limit to 100 pages for context
        pages_summary.append(
            f"[{row['PAGE_ID']}] {row['PAGE_TITLE']} ({row['CATEGORY']}) v{row['VERSION']}: "
            f"{row['ONE_LINE_SUMMARY'] or 'no summary'}"
        )

    # Sample content from pages for contradiction detection (first 20 pages)
    sample_content = []
    for row in pages[:20]:
        content_snippet = (row["CONTENT_MD"] or "")[:500]
        sample_content.append(f"### {row['PAGE_TITLE']}\n{content_snippet}")

    lint_prompt = f"""You are a wiki quality auditor for a manufacturing knowledge base.

Wiki statistics:
- Total pages: {total_pages}

All wiki pages:
{chr(10).join(pages_summary)}

Sample page content (first 20 pages):
{chr(10).join(sample_content)}

Perform a thorough health check and report:

1. **Contradictions**: Find any pages that make conflicting claims (different specs for same machine, conflicting safety info, etc.)
2. **Orphan pages**: Pages that are not referenced by other pages (missing cross-references)
3. **Stale claims**: Pages that reference dates/quarters that may now be outdated
4. **Missing pages**: Important entities mentioned in summaries but lacking their own page
5. **Incomplete pages**: Pages with very thin content that need expansion
6. **Missing cross-references**: Cases where two pages should link to each other but don't
7. **Data gaps**: Important information that appears missing from the wiki entirely

Format your response as a detailed markdown health report with:
- An executive summary with overall health score (0-100)
- A section for each issue type above
- Specific recommendations for improvement
- Priority actions (High/Medium/Low) for each finding"""

    lint_report = session.sql("""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-3-5-sonnet', ?) AS report
    """).bind([lint_prompt]).collect()[0]["REPORT"]

    duration_ms = int((time.time() - t0) * 1000)

    # Log the lint operation
    session.sql("""
        INSERT INTO MANUFACTURING_WIKI.KNOWLEDGE.INGESTION_LOG
            (OPERATION, DETAIL, STATUS, DURATION_MS)
        VALUES ('lint', ?, 'success', ?)
    """).bind([f"Linted {total_pages} pages", duration_ms]).collect()

    return lint_report
$$;

-- ============================================================
-- Cortex Search service over WIKI_PAGES (for hybrid mode)
-- Used at scale (>1000 wiki pages) as index becomes too large
-- ============================================================
CREATE OR REPLACE CORTEX SEARCH SERVICE WIKI_SEARCH
  ON CONTENT_MD
  ATTRIBUTES CATEGORY, PAGE_ID
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS (
  SELECT
    PAGE_ID,
    PAGE_TITLE,
    CATEGORY,
    CONTENT_MD,
    ONE_LINE_SUMMARY
  FROM MANUFACTURING_WIKI.KNOWLEDGE.WIKI_PAGES p
  JOIN MANUFACTURING_WIKI.KNOWLEDGE.WIKI_INDEX i USING (PAGE_ID)
);
