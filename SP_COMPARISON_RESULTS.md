# SP Comparison Test Results
## ANSWER_QUESTION vs ANSWER_QUESTION_HYBRID

**Date:** 2026-04-14  
**Original:** `MANUFACTURING_WIKI.KNOWLEDGE.ANSWER_QUESTION`  
**Hybrid:** `MANUFACTURING_SIMPLE.KNOWLEDGE.ANSWER_QUESTION_HYBRID`

---

## Setup

|                     | Original                                                                | Hybrid                                         |
| ------------------- | ----------------------------------------------------------------------- | ---------------------------------------------- |
| Retrieval unit      | LLM-compiled wiki pages (WIKI_PAGES table)                              | Raw text chunks (DOCUMENT_CHUNKS table)        |
| Index               | WIKI_SEARCH — Cortex Search on CONTENT_MD                               | MFG_CHUNK_SEARCH — Cortex Search on CHUNK_TEXT |
| Documents           | 110 wiki pages compiled from 63 PDFs                                    | 2,997 chunks from 63 PDFs                      |
| Cross-doc knowledge | Embedded in LLM system prompt (PROMPT_REGISTRY)                         | 7 explicit rows in DOMAIN_RELATION_RULES table |
| Routing             | Two-lane: point_lookup (1 page, ~200ms) or synthesis (8 pages, ~10-40s) | Single path: hybrid (8 chunks + COMPLETE)      |
| Stored procedures   | 7                                                                       | 1                                              |

---

## Test Q1: "Which production line had the highest downtime this week?"

### Original
- **Lane:** synthesis
- **Latency:** 19,799 ms
- **Sources:** 8 wiki pages (production-l7-operational-summary, production-l8-shift-analysis, production-l6-overview, production-l2-*, qc-l2-weekly-performance, production-l9-overview)
- **Answer:**
```
# Highest Downtime Production Line This Week

## Line L7 had the highest single-shift downtime

### Peak Downtime Event:
- ALERT: Line L7 — Mon 10/06 Day shift: 3.0 h downtime (exceeds 10% of shift)
- Week: Oct 01–07, 2025

## Other Notable High Downtime Events:

### Line L2 (Jan 01–07, 2025):
- ALERT: Mon 01/06 Day shift: 3.0 h (highest of week)
- Mon 01/06 Night: 2.8 h, Thu 01/02 Swing: 2.6 h

### Line L8 (Oct 01–07, 2025):
- ALERT: Sun 10/05 Swing: 2.7 h

### Line L6 (July 01–07, 2025):
- ALERT: Tue 07/01 Day shift: 3.0 h

## Summary:
Lines L7, L2, and L6 all recorded 3.0 h maximum single-shift downtimes during their
respective weeks. L7 is the most recent week (Oct 2025).
```

### Hybrid (first run — rules misfiring)
- **Lane:** hybrid
- **Latency:** 9,148 ms
- **Chunks retrieved:** 8 (doc_types: production, maintenance)
- **Rules applied:** 0 ← **BUG: doc_type mismatch** (rules keyed on `production_log`, data stored as `production`)
- **Answer:** "The question cannot be answered. Production logs lack shift-level downtime. Maintenance reports lack production line mapping."

### Hybrid (second run — rules fixed)
- **Latency:** 11,191 ms
- **Rules applied:** 7
- **Answer:** Still "cannot be determined" — the specific shift-level downtime numbers were not in the top 8 ranked chunks.

**Verdict: Original wins.** Wiki pages were LLM-compiled with explicit ALERT headings and structured downtime tables. Raw chunks are broader text fragments — the downtime numbers ranked outside the top 8 for this question.

---

## Test Q2: "Which machines on Line L4 have overdue maintenance tasks?"

### Original
- **Lane:** point_lookup
- **Latency:** ~3,000 ms (estimated)
- **Answer:**
```
# Line L4 Overdue Maintenance Machines

| Machine | Task ID  | Task Description               | Scheduled Date | Cost |
|---------|----------|-------------------------------|----------------|------|
| M072    | T736188  | Calibrate thermal compensation | 2025-04-19     | $313 |
| ...     | ...      | ...                           | ...            | ...  |

Based on ALERT: OVERDUE flags in the wiki context.
```

### Hybrid
- **Answer:** "Line L4 maintenance report MR-L4-Q3-2025 confirms 2 overdue tasks, but machine-level detail is not present in the retrieved chunks."

**Verdict: Original wins.** Machine-level rows in the maintenance report were split across chunk boundaries. The exact rows needed didn't rank in the top 8 chunks.

---

## Test Q3: "Which chemicals require temperature-controlled storage?"

### Original
- **Lane:** point_lookup
- **Answer:** Lists chemicals with explicit temperature ranges in a formatted table.

### Hybrid
- **Answer:** "All chemicals described in the retrieved SDS documents require temperature-controlled storage. Each specifies a defined temperature range."

**Verdict: Tie.** SDS documents are self-contained and factual. Storage requirements appear in short dense paragraphs that chunk cleanly. No cross-document reasoning required.

---

## Test Q4: "What QC defect rates were recorded for Line L7 this week?"

### Original
- **Answer:**
```
QC Defect Analysis — Line L7 Q2 2025
Total Defects Logged: 908 units across 120+ incidents
Defect Threshold: 3.4% | Actual: 3.36%
Top Defect Types: Dimensional out-of-spec: 21 incidents, machines M011...
```

### Hybrid
- **Answer:** "The QC report for Line L7 (QC-L7-Q2-2025) covers Q2 2025 (2025-10-01 to 2025-12-31). This is quarterly data, not weekly. Weekly breakdown is not available in the retrieved evidence."

**Verdict: Hybrid is more accurate.** The original returned quarterly figures for a "this week" question without flagging the mismatch. The hybrid correctly identified the temporal granularity gap and refused to misrepresent quarterly data as weekly.

---

## Bug Discovered During Testing: DOC_TYPE Mismatch

The data copied from MANUFACTURING_WIKI used short-form DOC_TYPE values:

| Stored in MANUFACTURING_SIMPLE | Domain rules expected |
|---|---|
| `production` | `production_log` |
| `maintenance` | `maintenance_report` |
| `qc` | `qc_report` |
| `sds` | `safety_data_sheet` |
| `fmea` | `fmea_worksheet` |
| `equipment_spec` | `equipment_spec` ✓ |

**Impact:** All 7 rules returned `rules_applied: 0` on the first Q1 run — domain knowledge was silently disabled.  
**Fix:** 7 SQL UPDATEs to the DOMAIN_RELATION_RULES table. No redeployment needed.  
**Lesson:** This highlights both the advantage (rules are easily fixed in SQL) and a risk (mismatch is silent unless you inspect `rules_applied` in the response).

---

## Summary Scorecard

| Question | Original | Hybrid | Notes |
|---|---|---|---|
| Q1 — Cross-line downtime comparison | ✓ Correct | ✗ Wrong | Wiki pages explicitly surfaced the comparison data |
| Q2 — Machine-level point lookup | ✓ Correct | ⚠ Partial | Chunk boundaries split machine-level rows |
| Q3 — Chemical storage requirements | ✓ Correct | ✓ Correct | Factual SDS data chunks cleanly |
| Q4 — QC defect rates | ⚠ Imprecise | ✓ More honest | Hybrid correctly flagged weekly vs quarterly mismatch |

---

## Latency Comparison

| SP | Q1 | Notes |
|---|---|---|
| ANSWER_QUESTION (original) | 19,799 ms | Two LLM calls: classify + synthesis |
| ANSWER_QUESTION_HYBRID | 9,148–11,191 ms | One LLM call: synthesis only |

Hybrid is ~2x faster because it skips the classifier LLM call and the category-routing step.

---

## Conclusions

**Original approach strengths:**
- Pre-compiled wiki pages explicitly surface structured facts (ALERT flags, tables, comparisons)
- Two-lane routing optimises point lookups to ~200ms without an LLM call
- Answer quality is high for aggregation and cross-entity comparison questions

**Hybrid approach strengths:**
- No ingest-time LLM cost — just chunking
- Domain rules are transparent, auditable, and editable without redeployment
- More honest about data gaps (Q4 example)
- ~2x faster at query time (no classifier call)
- Simple: 1 SP vs 7, 3 tables vs 5

**Hybrid approach weaknesses:**
- Chunk boundary splitting can exclude critical facts from the top-N results
- Raw chunks lack the structured context that LLM-compiled wiki pages provide
- DOC_TYPE values must exactly match rule keys — silent failure if they don't

**Recommended pattern:**
Use pre-compiled wiki pages (original approach) when answer quality is critical and the domain has structured, entity-centric documents. Use the hybrid approach when you need lower ingest cost, explainable domain rules, or faster iteration on the knowledge base. Consider combining both: use chunks for initial retrieval ranking, then pass retrieved wiki pages (if available) to the LLM for synthesis.
