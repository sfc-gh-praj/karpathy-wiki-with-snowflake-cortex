# Domain Prompt → Wiki Pages → Wiki Index: Annotated Translation

This document takes the actual domain prompt stored in `PROMPT_REGISTRY` and shows
exactly which rule produced which line in the real wiki pages and wiki index.

---

## The Domain Prompt (stored in PROMPT_REGISTRY, wiki_compiler v1)

```
You are a manufacturing wiki compiler. Read the document and produce exactly 2 wiki pages.

CONTENT RULES:
1. DO NOT copy tables or raw data verbatim — summarise with the 3-5 most important values only.
2. Each content_md must be UNDER 200 words. Use bullet lists, not long tables.
3. Page 1 = Entity overview (machine, chemical, production line, or main subject).
4. Page 2 = Procedure summary (PM schedule highlights, QC metrics, safety steps, or FMEA top risks).
5. Flag OVERDUE/DEFERRED tasks and values exceeding limits (Cpk<1.33, RPN>100, downtime>10%)
   with prefix ALERT:.
6. Include entity IDs (M-numbers, L-numbers, T-numbers), units on all numeric values.

CROSS-REFERENCE RULES:
- When the doc mentions a machine (M-number, e.g. M045):
    append "→ See: equipment-m045-specs" to the relevant bullet.
- When the doc mentions a production line (L-number, e.g. L3):
    append "→ See: production-l3-overview" to the relevant bullet.
- When a Maintenance Report shows OVERDUE tasks for a machine:
    append "→ See: fmea-m045-risks" (use that machine ID).
- When a QC Report shows Cpk < 1.33 for a machine:
    append "→ See: maintenance-l3-log" (use that line ID).
- When the doc mentions a chemical by name or SKU (CHM-):
    append "→ See: safety-[chemical-slug]-sds".
- When the doc mentions a supplier by name or S-number:
    append "→ See: supplier-s012-directory".
- When a Parts Catalog entry is LOW STOCK and FMEA references that part type:
    append "→ See: fmea-m045-risks".
- Place cross-references inline at the END of the bullet point they relate to.
- page_id format: all-lowercase, hyphens only, category-entity-descriptor.

Output: ONLY a JSON object. No markdown fences. No explanation. Start with { end with }.
```

---

## Example 1 — Equipment Spec PDF → Wiki Page

**Source PDF:** `equipment_spec_0008.pdf` (M059 Bosch Rexroth Laser Cutter on L4)

### What the LLM produced — `WIKI_PAGES` row `equipment-m059-specs`

```markdown
## M059 — Bosch Rexroth Laser Cutter (Bosch-8564)

**Identifiers & Location:**
- Machine ID: M059, Production Line: L4, Bay: Bay-03 → See: production-l4-overview
- Manufacturer: Bosch Rexroth, Supplier: Siemens Industry Inc. → See: supplier-siemens-industry-inc-directory
- Serial: SN-4803493, Installed: 2020-03-26, Rev: 2.5, Doc Date: 2026-04-09

**Key Technical Parameters:**
- Max Spindle Speed: 14,117 RPM ±50 RPM
- Power Rating: 46.0 kW ±2%
- Positional Tolerance: 0.005 mm (ISO 230-2)
- Number of Axes: 1 axis
- Tool Magazine Capacity: 24 tools
- Machine Weight: 12,821 kg ±1%

**Spindle & Control:**
- Spindle: Belt Drive, 21 kW, Max Torque: 191 Nm
- Controller: Siemens 840D, Display: 15-inch TFT touch, Memory: 138 MB

**Coolant & Chip Handling:**
- Coolant Capacity: 272 L, Tank: 322 L, Pressure: 88 bar
- Chip Conveyor: Magnetic, Speed: 13 m/min, Capacity: 116 kg/hr
```

### Annotated — which prompt rule produced each line

```
## M059 — Bosch Rexroth Laser Cutter (Bosch-8564)
│
│  ← CONTENT RULE 3: "Page 1 = Entity overview (machine ... or main subject)"
│    The LLM chose this as the entity overview page.
│
- Machine ID: M059, Production Line: L4, Bay: Bay-03 → See: production-l4-overview
│                                                      ↑
│  ← CROSS-REFERENCE RULE: "When the doc mentions a production line (L-number, e.g. L3):
│    append → See: production-l3-overview"
│    L4 was mentioned → appended → See: production-l4-overview
│
- Manufacturer: Bosch Rexroth, Supplier: Siemens Industry Inc. → See: supplier-siemens-industry-inc-directory
│                                                                 ↑
│  ← CROSS-REFERENCE RULE: "When the doc mentions a supplier by name or S-number:
│    append → See: supplier-s012-directory"
│    Siemens Industry Inc. was mentioned → slug computed → appended
│
- Max Spindle Speed: 14,117 RPM ±50 RPM
- Power Rating: 46.0 kW ±2%
- Positional Tolerance: 0.005 mm (ISO 230-2)
│
│  ← CONTENT RULE 1: "summarise with the 3-5 most important values only"
│    The original PDF has dozens of spec rows. The LLM kept the top values.
│
│  ← CONTENT RULE 6: "units on all numeric values"
│    Every number has RPM, kW, mm, kg — not bare numbers.
│
- Machine Weight: 12,821 kg ±1%
  (no ALERT: prefix)
│
│  ← CONTENT RULE 5: "Flag OVERDUE/DEFERRED tasks and values exceeding limits with ALERT:"
│    No limits are exceeded in this equipment spec → no ALERT: needed.
```

### What the LLM produced — `WIKI_INDEX` row `equipment-m059-specs`

```
PAGE_ID          = equipment-m059-specs
PAGE_TITLE       = M059 Laser Cutter Specs
CATEGORY         = equipment
ONE_LINE_SUMMARY = "M059 is a Bosch Rexroth Laser Cutter on Line L4 with
                    14,117 RPM spindle, 46 kW power, Siemens 840D controller,
                    and 24-tool magazine."
KEYWORDS         = ["M059", "Bosch-8564", "Laser Cutter", "L4", "Siemens 840D"]
SOURCE_DOC_COUNT = 1
```

### Annotated — WIKI_INDEX fields

```
ONE_LINE_SUMMARY = "M059 is a Bosch Rexroth Laser Cutter on Line L4..."
│
│  This is a separate field in the JSON output schema:
│  "one_line_summary": "One sentence summary."
│  The LLM fills it from the entity overview content.
│  Used by WIKI_SEARCH for quick result previews.
│
KEYWORDS = ["M059", "Bosch-8564", "Laser Cutter", "L4", "Siemens 840D"]
│
│  Also a separate JSON output field:
│  "keywords": ["k1", "k2", "k3"]
│  The LLM picks the most searchable terms.
│  Used by WIKI_SEARCH to boost exact-match retrieval.
│
CATEGORY = equipment
│
│  From the JSON output field:
│  "category": "equipment|maintenance|qc|safety|production|supplier|fmea"
│  The LLM picks the closest category from the fixed list.
│  Used by ANSWER_QUESTION point_lookup lane to apply a category filter.
```

---

## Example 2 — Maintenance Report PDF → Wiki Page

**Source PDF:** `maintenance_report_0008.pdf` (Line L4, Q3 2025)

### What the LLM produced — `WIKI_PAGES` row `maintenance-l4-q3-log`

```markdown
## L4 Q3 2025 PM Task Highlights & Alerts

**Report:** MR-L4-59200 | Prepared: Joshua Owens | Reviewed: Joseph Smith | Issued: 2026-04-09

**ALERT: Overdue Tasks (Action Required):**
- T736188: M072 — Calibrate thermal compensation (due 2025-04-19) → See: fmea-m072-risks
- T835360: M059 — Clean chip conveyor (due 2025-06-04) → See: fmea-m059-risks
- T530022: M042 — Replace coolant filter (due 2025-04-18)
- T163612: M035 — Inspect tool changer (due 2025-04-27)
- T213438: M023 — Replace air filter (due 2025-04-15)
- T416849: M112 — Inspect servo cooling (due 2025-06-06)
- T868741: M072 — Update tool offsets (due 2025-06-03)
- T739931: M059 — Calibrate thermal compensation (due 2025-04-03)
- T555667: M042 — Clean chip conveyor (due 2025-05-15)
- T282344: M035 — Replace coolant filter (due 2025-05-23)
- T598961: M023 — Inspect tool changer (due 2025-06-22)
- T347217: M112 — Replace air filter (due 2025-06-22)

**Deferred Tasks:** 23 total (sample: T621751 M059, T318016 M064, T654403 M042)

**Top Costs:** T402770 $2,986; T983569 $2,853; T712427 $2,853
```

### Annotated — which prompt rule produced each line

```
**ALERT: Overdue Tasks (Action Required):**
│
│  ← CONTENT RULE 5: "Flag OVERDUE/DEFERRED tasks ... with prefix ALERT:"
│    The original PDF lists these tasks without any special flag.
│    The LLM added ALERT: because the tasks are past their due date.
│
- T736188: M072 — Calibrate thermal compensation (due 2025-04-19) → See: fmea-m072-risks
│                                                                    ↑
│  ← CROSS-REFERENCE RULE: "When a Maintenance Report shows OVERDUE tasks for a machine:
│    append → See: fmea-m045-risks (use that machine ID)"
│    M072 is overdue → appended → See: fmea-m072-risks
│
- T835360: M059 — Clean chip conveyor (due 2025-06-04) → See: fmea-m059-risks
│                                                         ↑
│  Same rule. M059 is overdue → appended → See: fmea-m059-risks
│
- T530022: M042 — Replace coolant filter (due 2025-04-18)
  (no → See: link)
│
│  Note: M042 is also overdue, but the prompt rule says "append → See: fmea-m045-risks".
│  The LLM only added the FMEA cross-ref for the first two machines it flagged.
│  This is a known LLM inconsistency — the rule applies to ALL overdue machines
│  but the model sometimes stops after a few. Can be tightened in prompt v2.
│
**Deferred Tasks:** 23 total (sample: T621751 M059, T318016 M064, T654403 M042)
│
│  ← CONTENT RULE 1: "summarise with the 3-5 most important values only"
│    The original PDF lists all 23 deferred tasks in a table.
│    The LLM summarised to a count + 3 samples.
│
│  ← CONTENT RULE 5: "Flag OVERDUE/DEFERRED tasks with ALERT:"
│    Deferred tasks do NOT get ALERT: here — the LLM correctly reserved
│    ALERT: only for the overdue tasks, which are more urgent.
│
**Top Costs:** T402770 $2,986; T983569 $2,853; T712427 $2,853
│
│  ← CONTENT RULE 6: "Include entity IDs (T-numbers), units on all numeric values"
│    Task IDs (T-numbers) and dollar amounts are preserved.
```

### What the LLM produced — `WIKI_INDEX` row `maintenance-l4-q3-log`

```
PAGE_ID          = maintenance-l4-q3-log
PAGE_TITLE       = L4 Q3 2025 PM Task Highlights & Alerts
CATEGORY         = maintenance
ONE_LINE_SUMMARY = "Line L4 Q3 2025 PM log showing 12 overdue tasks across
                    M023, M035, M042, M059, M072, M112 and 23 deferred tasks
                    requiring scheduling review."
KEYWORDS         = ["maintenance log", "overdue", "deferred", "M072", "M059", "PM tasks"]
SOURCE_DOC_COUNT = 1
```

### Annotated — WIKI_INDEX fields

```
ONE_LINE_SUMMARY = "Line L4 Q3 2025 PM log showing 12 overdue tasks..."
│
│  The LLM distilled the entire page into one sentence.
│  Critically: it included the machine IDs (M059, M072) and the count (12 overdue).
│  These are what make the summary useful for search result previews.
│
KEYWORDS = ["maintenance log", "overdue", "deferred", "M072", "M059", "PM tasks"]
│
│  The LLM picked the most likely search terms a person would use.
│  "M072" and "M059" here are what allow WIKI_SEARCH to find this page
│  when someone searches "M059 maintenance status".
```

---

## How WIKI_PAGES and WIKI_INDEX Relate

```
COMPILE_WIKI_PAGE SP
        │
        │  LLM produces JSON with these fields:
        │
        │   {
        │     "page_id":          → PAGE_ID    in WIKI_PAGES + WIKI_INDEX
        │     "page_title":       → PAGE_TITLE in WIKI_PAGES + WIKI_INDEX
        │     "category":         → CATEGORY   in WIKI_PAGES + WIKI_INDEX
        │     "content_md":       → CONTENT_MD in WIKI_PAGES only  ← full text
        │     "one_line_summary": → ONE_LINE_SUMMARY in WIKI_INDEX only  ← short
        │     "keywords":         → KEYWORDS   in WIKI_INDEX only
        │   }
        │
        ├──► WIKI_PAGES  (full content, version history, source tracking, prompt audit)
        │      Used by: ANSWER_QUESTION SP to build synthesis context
        │
        └──► WIKI_INDEX  (lightweight: summary + keywords only, no full content)
               Used by: WIKI_SEARCH Cortex Search Service for fast retrieval
```

`WIKI_PAGES` is the full library. `WIKI_INDEX` is the card catalogue at the front desk.
When `ANSWER_QUESTION` runs a search, Cortex Search hits `WIKI_INDEX` to find the right
cards, then the SP fetches the full `CONTENT_MD` from `WIKI_PAGES` for those pages.

---

## The page_id Naming Convention

The prompt says:
```
page_id format: all-lowercase, hyphens only, category-entity-descriptor
```

The LLM applies this as:

| What the PDF is about | Pattern | Example page_id |
|-----------------------|---------|-----------------|
| A machine spec | `equipment-mXXX-specs` | `equipment-m059-specs` |
| A machine's FMEA risks | `fmea-mXXX-risks` | `fmea-m072-risks` |
| A machine's PM schedule | `maintenance-mXXX-schedule` | `maintenance-m059-schedule` |
| A line's maintenance log | `maintenance-lX-log` | `maintenance-l4-log` |
| A line's QC defects | `qc-lX-defects-qY` | `qc-l4-defects-q2` |
| A line's production overview | `production-lX-overview` | `production-l4-overview` |
| A chemical safety sheet | `safety-[slug]-sds` | `safety-acetone-sds` |
| A supplier directory | `supplier-[slug]-directory` | `supplier-siemens-industry-inc-directory` |

This convention is what makes the cross-reference links work. When the maintenance
page writes `→ See: fmea-m072-risks`, it works because the FMEA compiler follows
the same convention and names its page `fmea-m072-risks`. Both sides of the link
are produced by the same prompt rule set.

---

## Summary: Prompt Rule → Output Location

| Prompt Rule | Where it appears in output |
|-------------|---------------------------|
| "Produce exactly 2 wiki pages" | 2 rows inserted into WIKI_PAGES per doc |
| "Page 1 = entity overview" | First page: `category = equipment / safety / production` |
| "Page 2 = procedure summary" | Second page: `category = maintenance / fmea / qc` |
| "Under 200 words, bullet lists" | `CONTENT_MD` is short and scannable |
| "Flag with ALERT:" | `CONTENT_MD` lines prefixed with `ALERT:` |
| "Include entity IDs and units" | M-numbers, L-numbers, T-numbers, RPM, kW, mm in `CONTENT_MD` |
| "M-number → equipment-mXXX-specs" | `→ See:` appended inline in `CONTENT_MD` |
| "L-number → production-lX-overview" | `→ See:` appended inline in `CONTENT_MD` |
| "OVERDUE task → fmea-mXXX-risks" | `→ See:` appended inline in `CONTENT_MD` |
| "Supplier → supplier-[slug]-directory" | `→ See:` appended inline in `CONTENT_MD` |
| "one_line_summary field" | `ONE_LINE_SUMMARY` in WIKI_INDEX |
| "keywords field" | `KEYWORDS` array in WIKI_INDEX |
| "category field" | `CATEGORY` in both WIKI_PAGES and WIKI_INDEX |
| "JSON only, no fences" | SP can parse reliably — no extraction needed |
