# End-to-End Flow: "Which production line had the highest downtime this week?"

## Overview

This document traces every step from user question to final answer, including
which wiki pages were retrieved, which PDFs they came from, and how the LLM
synthesised a cross-line comparison.

---

## Step 1 — User fires the question

The user types (or clicks the chip):

> **"Which production line had the highest downtime this week?"**

The Streamlit app calls:
```python
answer_question(session, question)
# → CALL MANUFACTURING_WIKI.KNOWLEDGE.ANSWER_QUESTION('Which production line had the highest downtime this week?')
```

---

## Step 2 — SP detects lane and category

Inside `ANSWER_QUESTION`, the SP uses an LLM call to classify the question:

| Field          | Value        | Reason                                              |
|----------------|--------------|-----------------------------------------------------|
| `lane`         | `synthesis`  | Requires aggregating data across multiple pages     |
| `category_filter` | `production` | Keyword "production line" maps to production category |

A **point_lookup** question would be "What is the OEE of Line L7?" (one page).
This question needs data from *multiple lines* → **synthesis lane**.

---

## Step 3 — Cortex Search retrieves 8 wiki pages

Because lane = `synthesis`, the SP sets `search_filter = None` (no category
restriction) and `search_limit = 8`. This is the **cross-category retrieval fix**
applied earlier — synthesis must search across all categories to compare lines.

Cortex Search runs a semantic search against `WIKI_SEARCH` (built on `WIKI_PAGES`)
and returns the 8 most relevant pages:

| # | Wiki Page ID                      | Page Title                                | Category   |
|---|-----------------------------------|-------------------------------------------|------------|
| 1 | `qc-l2-weekly-performance`        | Line L2 Weekly Performance Metrics        | qc         |
| 2 | `production-l9-overview`          | Production Line L9 — Power Transmission Shafts | production |
| 3 | `production-l8-shift-analysis`    | Line L8 Shift & Downtime Analysis         | production |
| 4 | `production-l7-operational-summary` | Line L7 Weekly Operational Highlights   | production |
| 5 | `production-l2-oee-metrics`       | L2 OEE & Shift Performance Metrics       | production |
| 6 | `production-l6-overview`          | Production Line L6 – Automotive Body Stampings | production |
| 7 | `production-l2-shift-performance` | Line L2 — Shift Performance & Quality Summary | production |
| 8 | `production-l2-oee-analysis`      | Line L2 OEE & Performance Summary        | production |

Note: Page #1 comes from the `qc` category. Because synthesis sets
`search_filter = None`, it was still retrieved — it contains weekly shift
downtime data that is relevant despite being classified as `qc`.

---

## Step 4 — Source PDF traceability

Each wiki page was compiled from one or more source PDFs. This is the full
chain from page → PDF:

| Wiki Page ID                      | Source PDF                   |
|-----------------------------------|------------------------------|
| `qc-l2-weekly-performance`        | `smoke_production_log.pdf`   |
| `production-l9-overview`          | `production_log_0034.pdf`    |
| `production-l8-shift-analysis`    | `production_log_0040.pdf`    |
| `production-l7-operational-summary` | `production_log_0038.pdf`  |
| `production-l2-oee-metrics`       | `production_log_0046.pdf`    |
| `production-l6-overview`          | `maintenance_report_0016.pdf` + `production_log_0036.pdf` |
| `production-l2-shift-performance` | `production_log_0042.pdf`    |
| `production-l2-oee-analysis`      | `production_log_0032.pdf`    |

**9 PDFs** contributed to this single answer.

To manually verify:
1. Open `production_log_0038.pdf` → Line L7 data, look for "Mon 10/06 downtime 3.0 h"
2. Open `production_log_0040.pdf` → Line L8 data, look for "Sun 10/05 Swing 2.7 h downtime"
3. Open `production_log_0036.pdf` + `maintenance_report_0016.pdf` → Line L6 data,
   look for "Tue 07/01 Day shift 3.0 h downtime"
4. Open `production_log_0032.pdf` / `_0042.pdf` / `_0046.pdf` → Line L2 data,
   look for "Mon 01/06 Day shift 3.0 h"
5. Open `smoke_production_log.pdf` → L2 QC weekly metrics with shift downtime table

---

## Step 5 — LLM synthesises the answer

The SP sends the `CONTENT_MD` of all 8 wiki pages plus the question to
`SNOWFLAKE.CORTEX.COMPLETE('claude-sonnet-4-5', ...)`. The LLM:

1. Extracts per-line highest single-shift downtime from each page
2. Builds a comparison table across all lines found
3. Identifies L7 as the answer for the most recent week (Oct 1–7, 2025)
4. Notes that L2 and L6 also hit 3.0 h but in different calendar weeks

### Actual answer returned (latency: 16,111 ms)

```
# Highest Downtime Production Line This Week

## Answer: Line L7 (October 1–7, 2025)

### Downtime Comparison

| Line | Week        | Highest Single Shift Downtime | Details                          |
|------|-------------|-------------------------------|----------------------------------|
| L7   | Oct 1–7, 2025 | 3.0 h                       | Mon 10/06 Day shift              |
| L2   | Jan 1–7, 2025 | 3.0 h                       | Mon 01/06 Day shift              |
| L6   | Jul 1–7, 2025 | 3.0 h                       | Tue 07/01 Day shift              |
| L8   | Oct 1–7, 2025 | 2.7 h                       | Sun 10/05 Swing shift            |
| L9   | Jul 1–7, 2025 | 2.3 h                       | Thu 07/03 Swing shift            |

ALERT: Line L7 - Mon 10/06 Day shift downtime 3.0 h (exceeds 10% of shift)

## Note
Multiple production lines show identical 3.0 h maximum downtime events during
their respective weeks. However, these represent different calendar weeks.
Line L7 recorded 3.0 h downtime during the most recent week of October 1–7, 2025.
```

---

## Step 6 — Cross-reference chain

The `production-l7-operational-summary` page (compiled from `production_log_0038.pdf`)
contains a cross-reference written by the domain prompt:

```
→ See: maintenance-l7-log
→ See: qc-l7-oee-metrics
```

This tells the user: if you want to investigate *why* L7 had 3.0 h downtime,
the related pages to read are the L7 maintenance log and L7 OEE metrics. These
cross-references were written by the LLM during wiki compilation, guided by the
domain prompt rules.

---

## Full data flow diagram

```
User question
     │
     ▼
ANSWER_QUESTION SP
     │
     ├─► LLM classify ──► lane=synthesis, category=production
     │
     ├─► Cortex Search (no category filter, limit=8)
     │        │
     │        ├─ qc-l2-weekly-performance   ← smoke_production_log.pdf
     │        ├─ production-l9-overview      ← production_log_0034.pdf
     │        ├─ production-l8-shift-analysis ← production_log_0040.pdf
     │        ├─ production-l7-operational-summary ← production_log_0038.pdf
     │        ├─ production-l2-oee-metrics   ← production_log_0046.pdf
     │        ├─ production-l6-overview      ← maintenance_report_0016.pdf
     │        │                                 production_log_0036.pdf
     │        ├─ production-l2-shift-performance ← production_log_0042.pdf
     │        └─ production-l2-oee-analysis  ← production_log_0032.pdf
     │
     ├─► CORTEX.COMPLETE (claude-sonnet-4-5)
     │        │
     │        └─ 8 wiki page contents + question
     │               │
     │               └─► synthesised answer: Line L7, 3.0 h, Oct 1–7 2025
     │
     └─► return JSON {answer, lane_used, duration_ms, sources[]}
              │
              ▼
         Streamlit UI
              │
              ├─ renders answer markdown
              └─ "Source Documents" expander
                   ├─ L7 Operational Summary → production_log_0038.pdf
                   ├─ L8 Shift & Downtime Analysis → production_log_0040.pdf
                   ├─ L6 Overview → maintenance_report_0016.pdf + production_log_0036.pdf
                   └─ ... (5 more pages / PDFs)
```

---

## Key design decisions visible in this flow

| Decision                                             | Effect on this question                                                                                    |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Synthesis lane: `search_filter = None`               | Retrieved L2 QC page (`qc` category) which had downtime data — would have been missed with category filter |
| `search_limit = 8` (synthesis) vs `1` (point_lookup) | Retrieved all 5 production lines for comparison                                                            |
| Cross-reference rules in domain prompt               | L7 page links to `maintenance-l7-log` and `qc-l7-oee-metrics` for drill-down                               |
| `get_source_pdfs()` in Streamlit                     | User can see exactly which PDF each wiki page was compiled from                                            |
