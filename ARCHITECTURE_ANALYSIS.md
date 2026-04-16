# Architecture Analysis: Wiki Search vs Raw Text Search

## 1. The Information Loss Problem

The LLM acts like an editor who reads a 50-page report and writes a 2-page summary.
The summary is great for common questions — but any detail that didn't make the cut
is simply gone from search.

### Measured retention across doc types

| PDF | Raw chars | Wiki chars | Retained |
|---|---|---|---|
| `qc_report_0030.pdf` | 32,148 | 1,723 | **5%** |
| `production_log_0034.pdf` | 29,983 | 1,810 | **6%** |
| `maintenance_report_0010.pdf` | 49,167 | 1,922 | **4%** |
| `fmea_worksheet_0058.pdf` | 41,259 | 1,698 | **4%** |

**~95% of each PDF's content is not reachable through Cortex Search on WIKI_PAGES.**

### What happens when you ask about a missing detail

```
You ask: "What is the torque spec for bolt M8 in maintenance_report_0010?"

Step 1 — Cortex Search scans WIKI_PAGES.CONTENT_MD
         The torque spec was in the raw PDF on page 3
         but the LLM did not include it in the 1,922-char summary
         → Cortex Search finds nothing relevant

Step 2 — ANSWER_QUESTION gets back 0 or wrong pages
         Returns: "No relevant wiki pages found"
         OR returns the maintenance page but the answer section
         has no torque spec → LLM says "not in context"

The raw PDF had the answer the whole time. It just was not reachable.
```

---

## 2. What the Wiki Layer Actually Does

The wiki layer is not primarily a search index. It has three other jobs:

### Job 1 — Structured browsing (Wiki tab)
The Wiki tab works because of `CATEGORY`, `PAGE_TITLE`, `ONE_LINE_SUMMARY`,
`PERIOD_LABEL`. Raw text has none of that structure. Without the wiki layer,
the browse/filter UI collapses entirely.

### Job 2 — Point lookup speed (Lane 1)
For "what is the OEE for L9 in Q3?" — the wiki has the answer pre-written as
clean markdown. The system returns it in ~200ms with zero LLM calls. Raw text
would always require a COMPLETE call: adds 5-10 seconds and costs tokens.

### Job 3 — Cross-document relationship hints
Wiki pages carry editorial cross-references:
`"Cpk: 0.02 — Process NOT CAPABLE → See: maintenance-l9-log"`

These are **LLM-invented pointers** written at compilation time. They do not
exist anywhere in the raw PDFs. They are useful navigation hints for humans
browsing the wiki, but they are not a reliability mechanism (see Section 4).

---

## 3. Search Layer Comparison

|                          | WIKI SEARCH        | RAW TEXT SEARCH    |
|--------------------------|--------------------|--------------------|
| Summary questions        | ✓ excellent        | ✗ fragmented       |
| KPI / metric lookup      | ✓ fast, structured | ✓ also works       |
| Detail / spec lookup     | ✗ 95% loss         | ✓ full fidelity    |
| Exact procedure steps    | ✗ often missing    | ✓ verbatim         |
| Cross-references         | ✓ baked in         | ✗ none             |
| Browse / filter UI       | ✓ has structure    | ✗ no structure     |
| Answer cleanliness       | ✓ clean markdown   | ✗ raw OCR noise    |
| Point lookup latency     | ✓ ~200ms, no LLM   | ✗ always needs LLM |

---

## 4. The Cross-Reference Problem

### What cross-references are

```
Wiki cross-reference example:
"ALERT: Cpk: 0.02 — Process NOT CAPABLE → See: maintenance-l9-log"
                                                    ↑
                      This pointer exists ONLY in the wiki.
                      The raw QC PDF has no idea maintenance-l9-log exists.
                      The raw maintenance PDF has no idea the QC report cited it.
```

Cross-references were **invented by the LLM during wiki compilation**. They are
editorial annotations, not a verified knowledge graph.

### Why cross-references do not solve completeness

| What you might hope cross-refs solve | What they actually do |
|---|---|
| Complete knowledge graph between docs | LLM-invented hints — not verified |
| Guarantee the related doc gets retrieved | No — retrieval still depends on Cortex Search ranking |
| Fill in the wiki's 95% information loss | No — they only point to other incomplete summaries |

Following a cross-reference from a QC wiki page to a maintenance wiki page still
lands you on a 4% summary of the maintenance PDF. The pointer is good; the
destination is still incomplete.

### Where cross-references actually matter

```
LANE 1 — point_lookup
  "What is the OEE for L9 Q3?"
  → Wiki returns pre-written answer with cross-ref hint to maintenance log
  → Cross-ref is USEFUL here as a navigation hint for the user
  → But if maintenance wiki is incomplete, the hint leads to a partial answer

LANE 2 — synthesis
  "Which lines have both Cpk failures AND overdue maintenance?"
  → Cortex Search retrieves up to 8 pages across multiple docs
  → The LLM reads QC + maintenance context TOGETHER in one prompt
  → It discovers the Cpk↔maintenance connection LIVE during synthesis
  → Pre-built cross-references are IRRELEVANT — the LLM builds
     connections dynamically from whatever context it receives
```

**Cross-references only matter for Lane 1 point_lookup** — and even there they
are human-facing navigation hints, not the mechanism for completeness.
For synthesis (Lane 2), the LLM builds all connections dynamically from the
retrieved context pool. Pre-built cross-refs add no value in that path.

### The retrieval recall insight

The only scenario where pre-built cross-refs genuinely help is when the
**retrieval step missed a related document** (i.e., Cortex Search ranked it too
low to include in the top N results). That is a retrieval recall problem.
The correct fix is better retrieval, not more cross-references.

---

## 5. Three Architecture Options

### Option A — Wiki only (current state)
```
Question → Cortex Search → WIKI_PAGES.CONTENT_MD (5% of data)
```
Fast and clean for summary questions. 95% of detail is unreachable.
Suitable if users mostly ask KPI/summary-level questions.

### Option B — Raw text only, no wiki
```
Question → Cortex Search → RAW_DOCUMENTS.PLAIN_TEXT (100% of data)
```
Full fidelity but every answer needs an LLM call. No structured browse.
Answer quality suffers from OCR noise, table fragments, running headers.
No cross-reference hints. Wiki tab stops working.

### Option C — Wiki first, raw text fallback (recommended)
```
Question → Cortex Search (wiki)  → high confidence? → answer from wiki
                                         ↓ no
           Cortex Search (raw)   → RAW_DOCUMENTS.PLAIN_TEXT chunks
                                         ↓
                                   LLM synthesizes from raw PDF text
```

Wiki handles the ~80% of questions that are summary/KPI level.
Raw text handles the ~20% detail gap.
Wiki layer still earns its place for browsing, speed, and navigation hints.

**Implementation requires:**
1. A `RAW_PAGE_CHUNKS` table — one row per PDF page (split on `\nPage N\n` markers
   already embedded in `PLAIN_TEXT` by `AI_PARSE_DOCUMENT`)
2. A second Cortex Search service indexing `RAW_PAGE_CHUNKS.PAGE_TEXT`
   with `DOC_ID`, `FILE_NAME`, `DOC_TYPE`, `PERIOD_LABEL`, `PAGE_NUM` as attributes
3. `ANSWER_QUESTION` updated: if wiki search returns < N results or low relevance,
   fall back to raw chunk search before calling COMPLETE

---

## 6. Summary of What Each Layer Contributes

```
WIKI_PAGES
  → Browse UI (categories, titles, summaries)
  → Point lookup (Lane 1) — fast, zero LLM cost
  → Human navigation hints (cross-references)
  → Clean structured markdown for answer generation

RAW_DOCUMENTS / RAW_PAGE_CHUNKS
  → Full fidelity — 100% of PDF content searchable
  → Detail queries (specs, procedures, exact values)
  → Synthesis accuracy — LLM builds connections from full text
  → Ground truth for validating wiki summaries

NEITHER layer alone is sufficient.
The wiki is the fast path and the browse layer.
The raw text fills the gap the wiki cannot cover.
Cross-references are a UX nicety, not the foundation for completeness.
```

---

## 7. The Fundamental Flaw in the Karpathy Wiki Pattern

### What the pattern was designed for

The Karpathy LLM-wiki pattern was conceived as a **knowledge presentation layer**
— an LLM acts as an editor, reads raw documents, and writes organised human-readable
articles that can be browsed and searched. It is excellent at that job.

It was never designed as a **knowledge preservation layer**. The moment the LLM
compiles a wiki page, you have a lossy one-way transformation with no mechanism
to know what was dropped, mischaracterised, or hallucinated.

### How it compares to standard RAG

```
Standard RAG (what most production knowledge bases use)
  PDF → chunk into 500-token pieces → embed → index → retrieve → answer
  Information loss: zero. You search and return the original text.
  Hallucination risk at ingest: none. No LLM touches the source at ingest time.

Karpathy wiki pattern
  PDF → LLM summarises into wiki pages → embed → index → retrieve → answer
  Information loss: ~95% (measured in Section 1).
  Hallucination risk at ingest: real. The wiki LLM can misread, invent,
  or omit facts during compilation — and those errors are then served
  as answers with no signal that they came from a summary, not the source.
```

The wiki pattern inserts a **lossy, hallucination-prone LLM transformation**
between the source document and the search index. Standard RAG removes that step
entirely. For Q&A reliability that step is a liability, not an asset.

### The three compounding failure modes

**Failure mode 1 — Silent omission**
The wiki LLM decided not to include a fact. The fact is gone. The system returns
"not found" or a wrong answer with full confidence. There is no warning to the
user that the answer came from a summary, not the original source.

**Failure mode 2 — Compilation hallucination**
The wiki LLM misread a table, transposed a number, or invented a cross-reference
that does not exist in the source PDF. That error is now indexed and served as a
wiki article. Cortex Search will confidently retrieve it. The Q&A LLM will
confidently repeat it. The user has no way to detect it without going back to
the original PDF — which defeats the purpose of the system.

**Failure mode 3 — Cross-reference chains on incomplete summaries**
The wiki LLM writes "Cpk failing — See: maintenance-l9-log". The user follows
the reference. The maintenance wiki page is a 4% summary of the original 49,167-
character report. The specific corrective action they needed was in the dropped 96%.
The cross-reference chain looks complete but leads to an incomplete answer.
The system gave the appearance of connected knowledge without the substance.

### Why this matters specifically for manufacturing

Manufacturing knowledge bases are not casual reference tools. They are used for:

- **Compliance audits** — exact procedure text is required, not a summary
- **Incident investigation** — every detail matters; omissions cause wrong root cause
- **Maintenance execution** — a wrong torque spec or a missing step causes equipment damage
- **Safety** — an incomplete SDS summary could omit a critical hazard

In these contexts a system that silently drops 95% of content and may hallucinate
the remaining 5% is not just incomplete — it is a reliability risk to depend on.

### What the pattern is genuinely good for

The Karpathy wiki pattern is well suited to use cases where completeness is not
the primary requirement:

| Use case | Why it works |
|---|---|
| Browse and discovery | Users explore what the corpus contains without knowing what to ask |
| Executive summaries | "Give me the overview of Q3 QC status" — completeness not critical |
| Corpus triage | Quickly identify which documents are relevant before reading originals |
| Structured tagging | Auto-assign categories, periods, keywords to unstructured PDFs |
| Human-readable articles | Nicer to read than raw OCR output |

None of these require the wiki to be complete or verbatim. They require it to be
useful and navigable. The pattern delivers on that.

### The correct role for the wiki pattern

```
WRONG — Wiki as the Q&A foundation
  User question → search wiki summaries → answer from summaries
  Problem: 95% information loss, hallucination at ingest, no fidelity guarantee

RIGHT — Wiki as the presentation layer over a RAG foundation
  User question → search raw chunks (full fidelity) → answer from source text
                                                             ↓
                                               Wiki provides browse UI,
                                               category structure, and
                                               human-readable summaries
                                               alongside the raw answer
```

The wiki layer should sit **above** the Q&A layer, not beneath it. It organises
and presents. The raw text layer answers reliably. They are complementary only
when assigned the correct roles.

### Verdict

For a knowledge base where users need **reliable, complete, auditable answers**:

- The Karpathy wiki pattern alone is not a sufficient Q&A foundation
- It is a strong presentation and discovery layer
- Standard RAG on the original documents is the reliable foundation for Q&A
- The wiki adds value on top of that, not instead of it

Building a knowledge base on wiki summaries alone is equivalent to building a
library where someone has already discarded 95% of every book and may have
rewritten parts of what remains. The catalogue looks complete. The content is not.

---

## 8. Does Layer 1 + Layer 2 Solve Everything?

Layer 1 = Standard RAG on RAW_DOCUMENTS.PLAIN_TEXT (chunked by page)
Layer 2 = Karpathy wiki on WIKI_PAGES.CONTENT_MD (current system)

### What the combination solves

**Information loss (95% drop)**
Layer 1 fixes this completely. RAG indexes the original text — nothing is dropped
at ingest time. If it is in the PDF, it is in the index.
Status: SOLVED.

**Ingest-time compilation hallucination**
No LLM touches the source document during RAG indexing. The wrong torque spec
the wiki LLM might have written never enters the index.
Status: SOLVED.

**Silent omission**
The wiki LLM's editorial decisions no longer gatekeep what is retrievable. Every
page of every PDF is a searchable chunk.
Status: SOLVED — replaced with a smaller, different problem (see below).

**Cross-reference chains leading to incomplete summaries**
If a wiki cross-ref points to maintenance-l9-log and the wiki page is only 4%
complete, Layer 1 fills the gap. The raw maintenance text is fully searchable so
the synthesis LLM gets the actual corrective action, not just the stub.
Status: SUBSTANTIALLY IMPROVED.

---

### What the combination does NOT fully solve

**1 — Retrieval recall gaps (the RAG version of silent omission)**

RAG does not eliminate the "can't find the answer" problem. It replaces the LLM
editorial gap with a semantic embedding gap.

```
Wiki omission:  The wiki LLM chose not to include the torque spec.

RAG gap:        The query "what torque for bolt M8?" embeds differently
                from the chunk "tighten fastener to 45 Nm per spec table 3"
                → the chunk scores low and is not retrieved
                → same result: answer not found
```

The RAG gap is generally smaller and more predictable than the wiki gap, but it
is not zero. Terminology mismatch between the question and the document is the
primary cause.

**2 — Chunk boundary fragmentation**

RAG splits documents into fixed-size chunks. A relevant fact that spans two
chunks — for example, a table header on one page and its data rows on the next —
may be split, making neither chunk sufficient on its own to answer the question.

The `\nPage N\n` markers already embedded in PLAIN_TEXT by AI_PARSE_DOCUMENT
help here because page-level chunking preserves document structure better than
token-count chunking. But it does not eliminate the problem entirely.

**3 — Cross-reference navigation still lands on wiki summaries**

Wiki cross-references (`→ See: maintenance-l9-log`) point to wiki page IDs.
Following one still takes you to a 4% summary, not the raw text. The system does
not automatically resolve a cross-reference to its corresponding raw chunks.

```
User reads: "Cpk failing → See: maintenance-l9-log"
Follows link → maintenance-l9-log wiki page (4% summary)
Raw text is available but is NOT wired to cross-reference navigation.

Fixing this requires redesigning cross-refs to resolve to raw chunk IDs,
not wiki page IDs — a non-trivial change to both ingest and the app.
```

**4 — Answer-time synthesis hallucination**

Layer 1 eliminates hallucination baked into the index at ingest time. It does not
eliminate hallucination during answer generation. The synthesis LLM still reads
retrieved chunks and writes an answer — it can still misstate, combine incorrectly,
or fabricate a detail that was almost but not quite in the context.

The meaningful difference: with raw chunks the source text is available for the
user to verify against. With wiki summaries the provenance of each claim is harder
to trace back to the original document.

**5 — OCR noise in raw answers**

Wiki pages are clean markdown. Raw chunks contain running headers, fragmented
tables, OCR artefacts, and repeated boilerplate. The synthesis LLM has to reason
through the noise. Answer quality for detail questions retrieved from raw chunks
is lower than from a pre-cleaned wiki page on the same topic.

---

### Summary table

| Issue                                     | Layer 1 + Layer 2 | Notes                                          |
|-------------------------------------------|-------------------|------------------------------------------------|
| 95% information loss                      | SOLVED            | RAG indexes 100% of source text                |
| Ingest-time hallucination                 | SOLVED            | No LLM involved at index time                  |
| Silent omission                           | MOSTLY SOLVED     | Replaced by smaller retrieval recall gap       |
| Cross-ref chains on incomplete summaries  | IMPROVED          | Raw fills the gap; navigation still hits wiki  |
| Retrieval recall gaps                     | NOT SOLVED        | Semantic mismatch — standard RAG problem       |
| Chunk boundary fragmentation              | PARTIALLY MITIGATED | Page-level chunking helps, not eliminates    |
| Cross-ref navigation to raw chunks        | NOT SOLVED        | Requires redesigning cross-ref resolution      |
| Answer-time synthesis hallucination       | NOT SOLVED        | Exists in any LLM-based Q&A system             |
| OCR noise in raw answers                  | NOT SOLVED        | Trade-off accepted for full fidelity           |

---

### The remaining problems are standard RAG problems

The issues that Layer 1 + Layer 2 cannot fully solve — retrieval recall gaps,
chunk fragmentation, answer-time hallucination — are not specific to this system.
They exist in every RAG implementation. Active research addresses them via
re-ranking, HyDE (hypothetical document embeddings), multi-hop retrieval, and
self-consistency checking.

The problems that were specific to the Karpathy pattern — ingest-time
hallucination, 95% information loss, editorial omission — are fully resolved by
adding Layer 1. That is the meaningful architectural improvement.

The combination does not produce a perfect system. It produces a system whose
remaining failure modes are well-understood, industry-standard RAG limitations
rather than structural flaws introduced by the wiki compilation step.
