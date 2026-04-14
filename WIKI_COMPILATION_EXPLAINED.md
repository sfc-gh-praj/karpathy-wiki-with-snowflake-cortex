# How Wiki Pages Are Created — Step by Step

The domain prompt is the engine behind every wiki page. This document traces the full
journey from a raw PDF to a searchable, cross-referenced wiki card.

---

## Step 1 — The PDF lands on a Snowflake stage

Someone uploads a PDF to `@MANUFACTURING_WIKI.KNOWLEDGE.MFG_STAGE`.

```
equipment_spec_0008.pdf  ←  raw factory document
```

This is just a file sitting in storage. Nothing has read it yet.

---

## Step 2 — `PARSE_NEW_DOCUMENTS` extracts the raw text

The first SP reads the PDF using `AI_PARSE_DOCUMENT` and stores the raw extracted
text in `RAW_DOCUMENTS`.

```sql
CALL MANUFACTURING_WIKI.KNOWLEDGE.PARSE_NEW_DOCUMENTS();
```

After this, `RAW_DOCUMENTS` has a row like:

```
DOC_ID    = 'equipment_spec_0008'
FILE_NAME = 'equipment_spec_0008.pdf'
DOC_TYPE  = 'equipment_spec'
RAW_TEXT  = 'Machine ID: M059, Serial: SN-4803493,
             Production Line: L4, Bay: Bay-03,
             Manufacturer: Bosch Rexroth,
             Max Spindle Speed: 9503 RPM,
             Power Rating: 38.0 kW,
             Daily PM: Check spindle oil level...
             ...(full unstructured text from PDF)'
```

The raw text is messy — just everything the OCR pulled out of the PDF, in order.

---

## Step 3 — `COMPILE_WIKI_PAGE` is called with that DOC_ID

```sql
CALL MANUFACTURING_WIKI.KNOWLEDGE.COMPILE_WIKI_PAGE('equipment_spec_0008');
```

This SP does 4 things in sequence.

---

### Step 3a — Fetch the domain prompt from `PROMPT_REGISTRY`

```python
prompt_rows = session.sql(
    "SELECT PROMPT_ID, PROMPT_TEXT FROM PROMPT_REGISTRY
     WHERE PROMPT_NAME = 'wiki_compiler' AND IS_ACTIVE = TRUE"
).collect()

system_prompt = prompt_rows[0]["PROMPT_TEXT"]   # the full domain prompt
prompt_id     = prompt_rows[0]["PROMPT_ID"]     # for audit trail
```

At this point the SP has:
- The **instructions** (domain prompt)
- The **raw content** (from `RAW_DOCUMENTS`)

---

### Step 3b — Call the LLM with both

```python
COMPLETE('claude-sonnet-4-5', [
    { "role": "system", "content": system_prompt },   # the domain prompt
    { "role": "user",   "content": raw_text }         # the PDF text
])
```

The LLM receives two things at once:

```
SYSTEM (domain prompt):
  "You are a manufacturing wiki compiler.
   Produce exactly 2 wiki pages.
   Flag ALERT: on overdue tasks and Cpk < 1.33.
   Add → See: links for every M-number, L-number, chemical, supplier..."

USER (raw PDF text):
  "Machine ID: M059, Production Line: L4,
   Max Spindle Speed: 9503 RPM,
   Daily PM: Check spindle oil level,
   Supplier: Siemens Industry Inc.
   ..."
```

The LLM reads both and produces a JSON response:

```json
{
  "wiki_pages": [
    {
      "page_id": "equipment-m059-specs",
      "page_title": "M059 Laser Cutter Specs",
      "category": "equipment",
      "content_md": "## M059 — Bosch Rexroth Laser Cutter\n- Line: L4, Bay-03 → See: production-l4-overview\n- Supplier: Siemens Industry Inc. → See: supplier-siemens-industry-inc-directory\n- Max Spindle Speed: 9503 RPM\n- Power: 38.0 kW",
      "one_line_summary": "M059 Laser Cutter on L4, 38kW, serviced by Siemens.",
      "keywords": ["M059", "laser cutter", "L4", "Bosch Rexroth"]
    },
    {
      "page_id": "maintenance-m059-schedule",
      "page_title": "M059 PM Schedule Summary",
      "category": "maintenance",
      "content_md": "## M059 PM Highlights\n- Daily: Check spindle oil (~7 min)\n- Weekly: Lubricate guide ways (~18 min)\n- Annual: Laser calibration (235–244 min)\n- Critical spare: Spindle bearings, 58-day lead → See: supplier-siemens-industry-inc-directory",
      "one_line_summary": "Daily 7-min checks, annual laser calibration required.",
      "keywords": ["M059", "PM", "spindle", "calibration"]
    }
  ]
}
```

**Domain prompt rules applied in this example:**

| Rule | What happened |
|------|---------------|
| 200-word cap | Short bullet lists, not full tables |
| Page 1 = entity overview | Machine identity, location, specs |
| Page 2 = procedure summary | PM schedule highlights only |
| L-number rule | L4 got `→ See: production-l4-overview` |
| Supplier rule | Siemens got `→ See: supplier-siemens-industry-inc-directory` |
| JSON only output | No markdown fences, no explanation text |

---

### Step 3c — Parse the JSON and write to `WIKI_PAGES`

The SP takes that JSON output and for each page inside `wiki_pages`:

- If `PAGE_ID` does not exist yet → **INSERT** a new row
- If `PAGE_ID` already exists → **UPDATE** the existing row and increment `VERSION`

```python
# New page
INSERT INTO WIKI_PAGES
  (PAGE_ID, PAGE_TITLE, CATEGORY, CONTENT_MD, SOURCE_DOCS, VERSION, PROMPT_ID)
VALUES
  ('equipment-m059-specs', 'M059 Laser Cutter Specs', 'equipment',
   '## M059 ...(content)...', ['equipment_spec_0008'], 1, '2ce97e17-...')

# Existing page (built up from multiple PDFs over time)
UPDATE WIKI_PAGES
SET CONTENT_MD  = '...(new content)...',
    SOURCE_DOCS = ARRAY_APPEND(SOURCE_DOCS, 'equipment_spec_0008'),
    VERSION     = VERSION + 1,
    PROMPT_ID   = '2ce97e17-...'
WHERE PAGE_ID = 'production-l4-overview'
```

The `PROMPT_ID` column records exactly which version of the domain prompt was used
to produce this page. `PROMPT_ID IS NULL` means the page was compiled before
`PROMPT_REGISTRY` existed — a built-in audit signal.

---

### Step 3d — `WIKI_SEARCH` picks it up

The Cortex Search Service `WIKI_SEARCH` indexes `WIKI_PAGES` automatically.
Once the row is written, the page is immediately searchable via
`SNOWFLAKE.CORTEX.SEARCH_PREVIEW`.

---

## The Full Flow in One Picture

```
equipment_spec_0008.pdf
         │
         │  AI_PARSE_DOCUMENT
         ▼
RAW_DOCUMENTS
  DOC_ID   = 'equipment_spec_0008'
  RAW_TEXT = (messy unstructured text from PDF)
         │
         │  COMPILE_WIKI_PAGE('equipment_spec_0008')
         │
         ├─① Fetch domain prompt from PROMPT_REGISTRY
         │       ↓
         │   system_prompt = "You are a wiki compiler...
         │                    produce 2 pages...
         │                    add → See: links..."
         │   prompt_id     = '2ce97e17-...'
         │
         ├─② COMPLETE(system_prompt + raw_text)
         │       ↓
         │   LLM reads instructions + PDF content
         │   writes structured JSON with page_id,
         │   content_md, cross-reference links
         │
         ├─③ Parse JSON → INSERT / UPDATE WIKI_PAGES
         │       ↓
         │   equipment-m059-specs       (new row, version 1)
         │   maintenance-m059-schedule  (new row, version 1)
         │   production-l4-overview     (updated, version 2,
         │                               SOURCE_DOCS now has 2 entries)
         │
         └─④ WIKI_SEARCH auto-indexes new/updated rows
                 ↓
         pages immediately searchable by ANSWER_QUESTION SP
```

---

## Why the Domain Prompt Is the Only Thing That Matters

Every decision about what ends up in a wiki page comes from the domain prompt:

| Prompt rule | Effect on WIKI_PAGES |
|-------------|----------------------|
| "Produce exactly 2 pages" | Every doc produces 2 rows |
| "Under 200 words" | `CONTENT_MD` stays short and scannable |
| "Flag with ALERT:" | ALERT: prefix appears in `CONTENT_MD` — easy to search |
| "M-number → `equipment-mXXX-specs`" | Cross-ref links written into `CONTENT_MD` |
| "JSON only output" | SP can parse the response reliably |

Change the prompt in `PROMPT_REGISTRY` (INSERT new version, flip `IS_ACTIVE`),
recompile, and every page changes shape — no SP redeployment needed.

---

## What `→ See: page-id` Actually Points To

Every `→ See:` string in `CONTENT_MD` is a pointer to another row in `WIKI_PAGES`.

```
WIKI_PAGES row: maintenance-l4-log
  CONTENT_MD = "...M059 overdue chip conveyor → See: fmea-m059-risks..."
                                                        │
                                                        │ points to
                                                        ▼
WIKI_PAGES row: fmea-m059-risks          ← another row in the same table
  CONTENT_MD = "RPN 648: Chip Conveyor chain breakage..."
  SOURCE_DOCS = ['fmea_worksheet_XXXX']  ← compiled from this PDF
```

It is not a database foreign key — it is plain text that the LLM wrote following
the prompt's naming convention. The naming convention is:

```
category - entity - descriptor

equipment - m059  - specs       →  equipment-m059-specs
fmea      - m059  - risks       →  fmea-m059-risks
safety    - acetone - sds       →  safety-acetone-sds
production - l4   - overview    →  production-l4-overview
maintenance - l4  - log         →  maintenance-l4-log
supplier  - siemens-industry-inc - directory  →  supplier-siemens-industry-inc-directory
```

The Streamlit UI reads `CONTENT_MD`, finds `→ See: page-id` patterns, and turns
them into clickable links that fetch the target row from `WIKI_PAGES`.
