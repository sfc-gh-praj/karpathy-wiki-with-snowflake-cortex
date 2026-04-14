# Scaling Analysis: Karpathy Wiki vs Cortex Search RAG
## Scenario: 10,000 PDFs × 100 pages = 1,000,000 pages

---

## Part 1 — Wiki Approach vs Pure RAG at Scale

### The Fundamental Problem

At 500 pages → ~100 wiki pages → index fits in one COMPLETE call (~5KB). Fine.

At 1,000,000 pages → ~50,000–100,000 wiki pages → index is **5–10MB**.
No LLM context window handles that. The flat index lookup at the core of
Karpathy's query flow collapses.

This is a structural ceiling, not a tuning problem.

---

### Performance — Query Latency

| Approach | Latency | Why |
|---|---|---|
| Pure wiki, flat index | **Broken** | 50K-page index overflows context window entirely |
| Pure Cortex Search RAG | 1–3s | Vector search is O(log n) — scales well |
| Wiki + hierarchical routing | 4–10s | Two LLM hops: route to domain → then answer |
| **Wiki pages as corpus for Cortex Search** | 2–5s | CS retrieves pre-synthesized wiki pages instead of raw chunks |
| Wiki + category-partitioned index | 3–7s | Route query to partition first, then flat index within partition |

The hybrid — **index the wiki pages themselves in Cortex Search, not the raw chunks**
— is the sweet spot at this scale. You get Cortex Search's retrieval speed with the
synthesis quality of pre-compiled wiki pages.

**Wiki hybrid query flow:**
```
Query
  │
  ▼
Cortex Search over WIKI_PAGES (not raw chunks)
  │
  ▼
Top 5 pre-synthesized pages (cross-referenced, tables intact)
  │
  ▼
COMPLETE(wiki_pages + question)
  │
  ▼
Answer + Citations
```

**Pure RAG query flow:**
```
Query
  │
  ▼
Cortex Search over raw chunks (~3M chunks)
  │
  ▼
Top 20 fragments (decontextualised, tables broken)
  │
  ▼
COMPLETE(chunks + question)
  │
  ▼
Answer (lower synthesis quality)
```

---

### Cost Breakdown

#### Ingest — One-Time Cost

| Operation | Volume | Unit Cost (est.) | Total |
|---|---|---|---|
| `AI_PARSE_DOCUMENT` | 1M pages | ~$0.01–0.02/page | $10,000–20,000 |
| `COMPLETE` for wiki compilation | 10,000 PDFs × ~4 calls × 30K tokens avg | ~$3/MTok input | $3,600 |
| `COMPLETE` output (wiki content) | 10,000 PDFs × ~4 calls × 3K tokens | ~$15/MTok output | $1,800 |
| Cortex Search indexing (wiki pages) | ~80,000 wiki pages | Low (embedding) | ~$200–500 |
| **Wiki hybrid total** | | | **~$16,000–26,000** |
| **Pure RAG total** (no wiki compilation) | 3M chunks, embed only | | **~$2,500** |

The wiki approach costs 8–10x more to ingest. That cost is paid once.

#### Per-Query Cost

| Approach | Tokens per query | Cost per query | At 1M queries/month |
|---|---|---|---|
| Pure Cortex Search RAG | ~8K input + 1K output | ~$0.04 | ~$40,000/mo |
| Wiki hybrid (CS + COMPLETE) | ~20K input + 2K output | ~$0.09 | ~$90,000/mo |
| Wiki flat index (only works ≤500 pages) | ~30K input + 2K output | ~$0.12 | ~$120,000/mo |

Wiki hybrid is ~2.2x more expensive per query than pure RAG.

---

### Time to Complete Ingest

| Phase | Sequential | Parallelised (20 concurrent) |
|---|---|---|
| `AI_PARSE_DOCUMENT` (10K PDFs) | ~28 hours | ~2–3 hours |
| `COMPLETE` wiki compilation (40K calls) | ~55 hours | ~4–6 hours |
| Cortex Search indexing (wiki pages) | ~1 hour | ~30 min |
| **Total** | **~84 hours** | **~7–10 hours** |

Pure RAG (no wiki compilation): ~1–2 hours total.

---

### Where the Wiki Approach Still Wins at Scale

Even with a hybrid, the pre-compilation advantage holds for manufacturing.

**Example: "Which suppliers have had quality issues correlated with our
highest-downtime machines in the last 2 quarters?"**

- **Pure RAG**: needs chunks from supplier catalogs, QC reports, and production
  logs to all land in top-K simultaneously. Statistically improbable across 3M
  chunks. Answer will be incomplete.
- **Wiki hybrid**: The wiki page "Supplier Quality Summary" was compiled from all
  7 supplier PDFs. The page "Line 4 Downtime Analysis" was compiled from
  production logs + maintenance reports. Cortex Search retrieves both
  pre-synthesized pages. One COMPLETE call answers the question fully.

---

### Recommendation at 10,000 PDFs

```
                    ┌─────────────────────────────────┐
                    │  Hybrid Architecture             │
                    │                                  │
  PDFs in Stage ───▶│  AI_PARSE_DOCUMENT               │
                    │       ↓                          │
                    │  COMPLETE → WIKI_PAGES table     │
                    │       ↓                          │
                    │  Cortex Search index             │
                    │  (over wiki pages, not raw PDF)  │
                    │       ↓                          │
                    │  Query: CS retrieval + COMPLETE  │
                    └─────────────────────────────────┘
```

| Question | Pure RAG wins | Wiki Hybrid wins |
|---|---|---|
| "What is the torque for bolt M8?" | Yes — exact chunk | Overkill |
| "Which machines need maintenance next month?" | Risky | Yes |
| "Summarise all quality issues involving Supplier X" | Misses 40%+ | Yes |
| "Contradictions between SDS and maintenance procedure?" | Never surfaces | Yes — flagged at ingest |
| Budget-constrained, low query volume | Yes | Too expensive |
| High query volume, complex synthesis questions | Breaks down | Pays for itself |

**At 10,000 PDFs: abandon the flat index, keep the wiki compilation step,
and put Cortex Search in front of the wiki pages — not in front of the raw PDFs.**

---

## Part 2 — Cortex Search with Attribute Indexes

### How Cortex Search Attributes Work

`ATTRIBUTES` columns in a Cortex Search service act as **pre-search partition
filters** — they narrow the chunk search space before vector similarity runs.

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE MFG_SEARCH
  ON parsed_text
  ATTRIBUTES doc_type,
             equipment_id,
             line_number,
             document_date
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS (
  SELECT parsed_text, doc_type, equipment_id, line_number, document_date
  FROM RAW_CHUNKS
);
```

At query time, filters execute before vector search:

```python
results = root.databases["MFG_DB"].schemas["MFG"] \
  .cortex_search_services["MFG_SEARCH"] \
  .search(
    query="scheduled maintenance overdue",
    columns=["parsed_text"],
    filter={"@and": [
      {"@eq": {"doc_type": "maintenance_report"}},
      {"@eq": {"equipment_id": "CNC_X500"}}
    ]},
    limit=10
  )
```

---

### Performance Impact at 1M Pages / 3M Chunks

| Filter scenario | Chunks searched | Latency |
|---|---|---|
| No filter | 3,000,000 | ~2–3s |
| `doc_type = 'maintenance'` (~10% of corpus) | 300,000 | ~0.5–0.8s |
| `doc_type = 'maintenance' AND equipment_id = 'X500'` | ~30,000 | ~0.2–0.4s |
| `doc_type = 'sds' AND line_number = '4'` | ~5,000 | <0.2s |

Well-designed attributes make Cortex Search fast at 1M pages for filtered queries.

---

### What Attribute Indexing Fixes vs. What It Doesn't

**Fixes:**
- Exact/filtered lookups: "All maintenance records for Line 4 in Q1"
  → `line_number=4, doc_type=maintenance, date>=Q1` → tiny search space
- Keyword + semantic hybrid on narrow corpus: BM25 + vector on 30K chunks
  is highly accurate
- Per-equipment queries: filter by `equipment_id`, search only relevant PDFs
- Reduces false positives significantly

**Does not fix:**
- Cross-category synthesis: "How does supplier quality correlate with machine
  downtime?" — needs chunks from `supplier_catalog` AND `qc_report` AND
  `production_log`. No single attribute filter helps.
- Table fragmentation: attributes don't change how tables are chunked.
  A FMEA row split across two chunks is still broken.
- Contradiction detection: never surfaces across documents.
- Multi-hop reasoning: "Which machines flagged in FMEA last year have had
  actual failures since?" — requires joining reasoning across two document
  types, not just retrieval.

---

### Revised Decision Matrix at 10,000 PDFs

| Query type | CS (no attrs) | CS with Attributes | Wiki Hybrid |
|---|---|---|---|
| "Torque spec for M8 bolt in X500" | Good | Excellent | Overkill |
| "All overdue maintenance for Line 4" | Noisy | Excellent | Good |
| "Supplier quality vs downtime correlation" | Poor | Still poor | Excellent |
| "Contradictions between SDS and procedure" | Never | Never | Yes (at ingest) |
| "Summarise all Q1 quality issues" | Incomplete | Incomplete | Excellent |
| Query latency | 2–3s | 0.3–0.8s | 2–5s |
| Cost per query | $0.04 | $0.04 | $0.09 |

---

### The Practical Recommendation — Two-Lane Architecture

```
                     User Question
                          │
                ┌─────────▼─────────┐
                │   Query Router    │
                │ (classify intent) │
                └────────┬──────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
  Filtered / point               Synthesis /
  lookup query                   cross-document query
          │                             │
          ▼                             ▼
  Cortex Search                  Wiki hybrid
  with Attributes                (CS over wiki pages
  (fast, cheap,                   + COMPLETE)
   $0.04/query,                   ($0.09/query,
   0.3–0.8s)                       2–5s)
```

The router is a single lightweight COMPLETE call — classify whether the
question needs a point lookup or synthesis. Cost is negligible.

---

### Recommended Attribute Design for Manufacturing

```sql
ATTRIBUTES
  doc_type,          -- 'maintenance', 'spec', 'qc', 'sds', 'production', 'fmea', 'catalog'
  equipment_id,      -- 'CNC_X500', 'LINE_4', etc.
  supplier_id,       -- for catalog/SDS lookups
  date_year_month,   -- '2025-01' for time-range filtering
  site_id            -- if multi-plant
```

With these five attributes, the majority of operational queries hit the filtered
path and are fast and cheap. The synthesis path handles analytical questions where
wiki pre-compilation earns its cost.

---

## Summary — Which Approach, When

| Scale | Recommendation |
|---|---|
| < 500 pages | Pure wiki, flat index. No Cortex Search needed. |
| 500–5,000 pages | Wiki hybrid: compile wiki, CS over wiki pages. |
| 5,000–50,000 pages | Two-lane: CS with attributes for point lookups + wiki hybrid for synthesis. |
| > 50,000 pages | Hierarchical wiki + CS with attributes mandatory. Wiki compilation may need batching strategy. |
