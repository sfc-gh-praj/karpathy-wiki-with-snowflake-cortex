# Project: Manufacturing Intelligence Wiki
## Context for Claude — Lessons Learned

This file captures constraints, known issues, and corrections discovered while
building this solution. Read this before making any changes to the codebase.

---

## 1. Streamlit in Snowflake (SiS) — Unsupported APIs

SiS runs an older pinned version of Streamlit. Many newer APIs fail at runtime.
**Always test against SiS, not the latest public Streamlit docs.**

### APIs that do NOT work in SiS

| What you might write | What to use instead |
|---|---|
| `st.container(horizontal=True)` | `st.columns(N)` and render into each column |
| `st.container(border=True)` | `st.container()` — border param silently breaks |
| `st.space("small")` | `st.write("")` |
| `st.metric(..., border=True)` | `st.metric(...)` — remove border kwarg |
| `st.column_config.TextColumn(...)` | Remove entire `column_config={}` from `st.dataframe()` |
| `st.dataframe(..., hide_index=True)` | Remove `hide_index` — not supported |
| `st.dataframe(..., pinned=True)` | Remove `pinned` from column configs |
| `st.dataframe(..., on_select="rerun", selection_mode=...)` | Use a `st.selectbox` or `st.multiselect` below the dataframe |
| `st.dataframe(..., key="name")` | Remove `key=` — not supported on `st.dataframe` |
| `st.rerun()` | `st.experimental_rerun()` |
| `st.set_page_config(layout="wide")` | Call is accepted but `layout` is ignored by SiS |

### Safe SiS APIs (confirmed working)
- `st.columns()`, `st.tabs()`, `st.expander()`, `st.divider()`
- `st.metric()`, `st.button()`, `st.selectbox()`, `st.multiselect()`, `st.text_area()`
- `st.markdown()`, `st.caption()`, `st.info()`, `st.warning()`, `st.error()`, `st.success()`
- `st.spinner()`, `st.progress()`, `st.dataframe()` (no keyword args beyond the data arg)
- `st.download_button()`, `st.radio()`, `st.checkbox()`, `st.text_input()`
- `unsafe_allow_html=True` in `st.markdown()`
- `st.session_state`, `st.experimental_rerun()`

---

## 2. Snowflake Models — Available in This Account

| Model string | Available? |
|---|---|
| `claude-sonnet-4-5` | YES — use this |
| `claude-3-5-sonnet` | NO — returns "Model unavailable" error |
| `claude-3-haiku` | Unverified |

Always use `claude-sonnet-4-5` in `SNOWFLAKE.CORTEX.COMPLETE(...)` calls.

The active LLM for `COMPILE_WIKI_PAGE` and `ANSWER_QUESTION` is also
`claude-sonnet-4-5` (stored in `PROMPT_REGISTRY`).

---

## 3. Snowpark Python SP API

### `.bind()` does not exist

The following pattern **fails at runtime**:
```python
# WRONG — bind() is not a Snowpark DataFrame method
session.sql("SELECT CORTEX.COMPLETE('model', ?) AS R").bind([prompt]).collect()
```

The correct pattern for parameterised queries in Snowpark:
```python
# CORRECT
session.sql(
    "SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-sonnet-4-5', ?) AS REPORT",
    params=[prompt]
).collect()
```

This applies to INSERT statements too:
```python
# CORRECT
session.sql(
    "INSERT INTO MY_TABLE (COL1, COL2) VALUES (?, ?)",
    params=[val1, val2]
).collect()
```

### Scripting blocks (DECLARE/BEGIN/END)

Snowflake scripting blocks cannot be executed directly via `snowflake_sql_execute`
or `snow sql -q`. They must be wrapped in a stored procedure or run via
`snow sql -f` (file-based execution).

---

## 4. Deploying SPs — Shell Escaping Pitfalls

When using `snow sql -q "..."` for inline SP creation:
- Square bracket array literals like `[lint_prompt]` get **stripped by the shell**
- The SP is created with `params=` (empty) instead of `params=[lint_prompt]`
- This causes silent runtime failures

**Always use `snow sql -f /path/to/file.sql` for stored procedures that contain
Python code with list literals, f-strings, or special characters.**

Avoid using `snow sql -q` for anything more complex than a simple SELECT or CALL.

### SP deployment requires USE DATABASE / USE SCHEMA

```sql
-- Always include these before CREATE PROCEDURE
USE DATABASE MANUFACTURING_WIKI;
USE SCHEMA KNOWLEDGE;
CREATE OR REPLACE PROCEDURE ...
```

Without them you get: `SQL access control error: Insufficient privileges to
operate on schema 'PUBLIC'`

---

## 5. SP Signatures — Always Verify Before Calling

Do not assume SP argument types from the SP name or description.
Always check first:

```sql
SELECT PROCEDURE_NAME, ARGUMENT_SIGNATURE, DATA_TYPE
FROM MANUFACTURING_WIKI.INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = 'KNOWLEDGE'
ORDER BY PROCEDURE_NAME;
```

### Actual signatures in this project

| Procedure | Signature | Returns |
|---|---|---|
| `ANSWER_QUESTION` | `(QUESTION VARCHAR, MAX_CONTEXT_PAGES NUMBER DEFAULT 8)` | VARIANT |
| `COMPILE_WIKI_PAGE` | `(DOC_ID VARCHAR)` | VARIANT |
| `COMPILE_ALL_WIKI` | `(MAX_DOCS NUMBER)` | VARIANT |
| `INGEST_ALL_NEW` | `(MAX_FILES NUMBER)` | VARIANT |
| `PARSE_NEW_DOCUMENTS` | `(MAX_FILES NUMBER)` | VARIANT |
| `LINT_WIKI` | `()` | VARCHAR |
| `RECOMPILE_REMAINING` | `()` | VARCHAR |

`ANSWER_QUESTION` has NO `save_to_wiki` boolean parameter — passing TRUE/FALSE
as the second argument causes `Invalid argument types (VARCHAR, BOOLEAN)`.

---

## 6. ANSWER_QUESTION Response Keys

The SP response JSON uses these exact keys — the app must read them correctly:

```json
{
  "answer":          "...",
  "lane_used":       "synthesis",
  "category_filter": "production",
  "duration_ms":     16111,
  "sources": [
    { "page_id": "production-l7-operational-summary", "title": "..." }
  ]
}
```

**Not** `lane`, `latency_ms`, or `citations` — those are wrong and return `None`.

---

## 7. Wiki Page Compilation — Non-Deterministic page_ids

The LLM generates slightly different `page_id` values on each run of
`COMPILE_WIKI_PAGE`. This means re-running the SP for the same document creates
**new pages** (INSERT) rather than updating existing ones (UPDATE), leaving
orphaned pages with `PROMPT_ID IS NULL`.

**Never re-run `COMPILE_ALL_WIKI_PAGES()` or `COMPILE_WIKI_PAGE()` on documents
that already have compiled pages.** Use `RECOMPILE_REMAINING()` which only
processes documents with zero PROMPT_ID page coverage.

To clean up orphaned pages after a recompile:
```sql
DELETE FROM WIKI_PAGES WHERE PROMPT_ID IS NULL;  -- removes old orphan pages
```

---

## 8. Streamlit Deployment

### snowflake.yml — do not include runtime_name

```yaml
# WRONG — triggers SPCS container mode, requires compute_pool
entities:
  my_app:
    type: streamlit
    runtime_name: SYSTEM$ST_CONTAINER_RUNTIME_PY3_11  # remove this line

# CORRECT — uses standard SiS runtime
entities:
  my_app:
    type: streamlit
    query_warehouse: QUICKSTART
```

### Deploy command
```bash
snow streamlit deploy --replace --connection COCO_JK
```

Run from the `streamlit/` directory (where `snowflake.yml` lives).

---

## 9. Snowflake Connection Details

| Purpose | Connection name |
|---|---|
| Snow CLI / SQL execution | `COCO_JK` |
| Snowpark agent session | `snowhouse` |
| Account | `SFSENORTHAMERICA-PRAJ01` |
| Warehouse | `QUICKSTART` |
| Role | `accountadmin` |
| Database | `MANUFACTURING_WIKI` |
| Schema | `KNOWLEDGE` |

---

## 10. Key Tables and Their Roles

| Table | Purpose |
|---|---|
| `RAW_DOCUMENTS` | One row per ingested PDF — stores extracted text |
| `WIKI_PAGES` | Compiled wiki pages with full `CONTENT_MD` |
| `WIKI_INDEX` | Lightweight index (no content) for browse/search UI |
| `PROMPT_REGISTRY` | Versioned domain prompts — `IS_ACTIVE=TRUE` row drives compilation |
| `INGESTION_LOG` | Audit log for all PARSE / COMPILE / ANSWER / lint operations |

Active prompt ID: `2ce97e17-0dd5-4603-8bd3-d23aee829da0` (wiki_compiler v1)

---

## 11. Synthesis Lane Bug — Already Fixed

The `ANSWER_QUESTION` SP originally applied `category_filter` to Cortex Search
in both the `point_lookup` and `synthesis` lanes. This broke cross-category
questions (e.g. a `production` category filter would miss `qc` pages that
contain production downtime data).

**Fix already applied in `snowflake/03_query_procedure.sql`:**
```python
search_limit = 1 if lane == "point_lookup" else max_context_pages
search_filter = category_filter if lane == "point_lookup" else None
pages = cortex_search(session, question, search_filter, search_limit)
```

Do not revert this — cross-category synthesis depends on it.
