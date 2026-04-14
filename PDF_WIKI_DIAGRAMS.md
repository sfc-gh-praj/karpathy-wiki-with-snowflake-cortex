# PDF Relationships, Wiki Structure & Domain Prompt — Visual Guide

All diagrams use [Mermaid](https://mermaid.js.org/) syntax.
Render in GitHub, VS Code (Markdown Preview), Notion, or https://mermaid.live

---

## Diagram 1 — The 7 PDF Types and What They Describe

Each PDF type covers a different slice of the factory universe.

```mermaid
graph TD
    subgraph FACTORY["🏭 Factory Universe"]
        M["Machines\nM001–M200"]
        L["Production Lines\nL1–L10"]
        C["Chemicals\nCHM-0001–CHM-0050"]
        S["Suppliers\nS001–S020"]
    end

    subgraph PDFS["📄 7 PDF Document Types"]
        ES["equipment_spec\n1 machine\ntech specs + PM schedule"]
        PC["parts_catalog\n3–5 machines\nspend + stock levels"]
        FM["fmea_worksheet\n1 machine\nfailure risks + RPN scores"]
        MR["maintenance_report\n1 line, 1 quarter\nPM tasks + downtime"]
        QC["qc_report\n1 line, 1 quarter\ndefects + Cpk"]
        PL["production_log\n1 line, 1 week\noutput + OEE"]
        SD["safety_data_sheet\n1 chemical\nGHS 16 sections"]
    end

    M -->|described by| ES
    M -->|described by| FM
    M -->|described by| PC
    L -->|described by| MR
    L -->|described by| QC
    L -->|described by| PL
    C -->|described by| SD

    style FACTORY fill:#e8f4f8,stroke:#2196F3
    style PDFS fill:#fff8e1,stroke:#FF9800
```

---

## Diagram 2 — How PDFs Compile Into Wiki Pages (The Domain Prompt in Action)

```mermaid
flowchart TD
    subgraph STAGE["❄️ Snowflake Stage\n@MFG_STAGE"]
        P1["equipment_spec_0008.pdf\nM059 Laser Cutter, L4"]
        P2["maintenance_report_0008.pdf\nLine L4, Q3 2025"]
        P3["qc_report_0026.pdf\nLine L4, Q2 2025"]
        P4["fmea_worksheet_0050.pdf\nMachine M128"]
        P5["safety_data_sheet_0024.pdf\nChemical CHM-0024"]
    end

    subgraph PROMPT["📋 PROMPT_REGISTRY\nwiki_compiler v1"]
        DP["Domain Prompt\n─────────────\nCONTENT RULES:\n• 2 pages per doc\n• 200 words max\n• ALERT: flags\n• entity IDs + units\n─────────────\nCROSS-REF RULES:\n• M-number → specs\n• L-number → overview\n• OVERDUE → FMEA\n• Cpk<1.33 → maint log\n• chemical → SDS\n• supplier → directory"]
    end

    subgraph SP["⚙️ COMPILE_WIKI_PAGE SP"]
        PARSE["① AI_PARSE_DOCUMENT\nextract raw text"]
        FETCH["② Fetch prompt\nfrom PROMPT_REGISTRY"]
        LLM["③ COMPLETE\ndomain prompt + raw text"]
        WRITE["④ INSERT/UPDATE\nWIKI_PAGES + WIKI_INDEX"]
    end

    subgraph WIKI["📚 WIKI_PAGES Table"]
        W1["equipment-m059-specs\ncategory: equipment"]
        W2["maintenance-m059-schedule\ncategory: maintenance"]
        W3["maintenance-l4-q3-log\ncategory: maintenance"]
        W4["production-l4-overview\ncategory: production"]
        W5["qc-l4-defects-q2\ncategory: qc"]
        W6["fmea-m128-risks\ncategory: fmea"]
        W7["safety-chm0024-sds\ncategory: safety"]
    end

    P1 --> PARSE
    P2 --> PARSE
    P3 --> PARSE
    P4 --> PARSE
    P5 --> PARSE
    PARSE --> FETCH
    DP --> FETCH
    FETCH --> LLM
    LLM --> WRITE

    WRITE -->|"2 pages from\nequipment_spec_0008"| W1
    WRITE -->|"2 pages from\nequipment_spec_0008"| W2
    WRITE -->|"2 pages from\nmaintenance_report_0008"| W3
    WRITE -->|"shared page built\nfrom 2 PDFs"| W4
    WRITE -->|"2 pages from\nqc_report_0026"| W5
    WRITE -->|"2 pages from\nfmea_worksheet_0050"| W6
    WRITE -->|"2 pages from\nsafety_data_0024"| W7

    style STAGE fill:#e3f2fd,stroke:#1565C0
    style PROMPT fill:#f3e5f5,stroke:#6A1B9A
    style SP fill:#e8f5e9,stroke:#2E7D32
    style WIKI fill:#fff8e1,stroke:#E65100
```

---

## Diagram 3 — The Cross-Reference Web (Real L4 Example)

This shows how `→ See:` links written into `CONTENT_MD` connect wiki pages
that were compiled from completely different PDFs.

```mermaid
graph LR
    subgraph EQ["📦 Equipment\nSource: equipment_spec_0008.pdf"]
        E1["equipment-m059-specs\nM059 Laser Cutter\nL4, Bay-03\n46kW, 14117 RPM"]
        E2["maintenance-m059-schedule\nM059 PM Schedule\nDaily 7min\nAnnual laser cal"]
    end

    subgraph MNT["🔧 Maintenance\nSource: maintenance_report_0008.pdf"]
        M1["maintenance-l4-q3-log\nALERT: 12 OVERDUE tasks\nM059, M072, M042...\n23 deferred"]
        M2["maintenance-l4-q3-2025-summary\nL4 Q3 summary\nTop costs\nDeferred schedule"]
    end

    subgraph QC["📊 QC\nSource: qc_report_0026.pdf"]
        Q1["qc-l4-defects-q2\nCpk = 0.06 ALERT\n14 dimensional defects\n10 machines flagged"]
        Q2["qc-metrics-l4-q2-2025\nOEE = 81.4% ALERT\nDefect rate 3.04%\ntarget ≤ 3.2%"]
    end

    subgraph PROD["🏭 Production\nSource: maint_0008 + qc_0026"]
        P1["production-l4-overview\nLine L4\nHydraulic Manifold Blocks\nQ2 2025"]
    end

    subgraph FMEA["⚠️ FMEA\nSource: fmea_worksheet PDFs"]
        F1["fmea-m059-risks\n⚡ forward reference\nno FMEA PDF for M059\nin current dataset"]
        F2["fmea-m072-risks\n⚡ forward reference\nno FMEA PDF for M072\nin current dataset"]
    end

    subgraph SUP["🏢 Supplier"]
        S1["supplier-siemens-industry-inc-directory"]
    end

    E1 -->|"L-number rule\nL4 mentioned"| P1
    E1 -->|"supplier rule\nSiemens mentioned"| S1
    E2 -->|"supplier rule\nspare parts supplier"| S1
    M1 -->|"OVERDUE rule\nM072 overdue"| F2
    M1 -->|"OVERDUE rule\nM059 overdue"| F1
    Q1 -->|"Cpk<1.33 rule\nCpk=0.06"| M1
    Q2 -->|"Cpk<1.33 rule"| M1
    P1 -->|"Cpk<1.33 rule\naggregated page"| M1

    style EQ fill:#e3f2fd,stroke:#1565C0
    style MNT fill:#e8f5e9,stroke:#2E7D32
    style QC fill:#fff8e1,stroke:#E65100
    style PROD fill:#fce4ec,stroke:#880E4F
    style FMEA fill:#ffebee,stroke:#B71C1C
    style SUP fill:#f3e5f5,stroke:#4A148C
```

---

## Diagram 4 — Which Domain Prompt Rule Creates Which Arrow

```mermaid
graph TD
    subgraph PROMPT_RULES["Domain Prompt Cross-Reference Rules"]
        R1["Rule 1\nM-number mentioned\n→ See: equipment-mXXX-specs"]
        R2["Rule 2\nL-number mentioned\n→ See: production-lX-overview"]
        R3["Rule 3\nOVERDUE maintenance task\n→ See: fmea-mXXX-risks"]
        R4["Rule 4\nCpk < 1.33 in QC report\n→ See: maintenance-lX-log"]
        R5["Rule 5\nChemical name / CHM-\n→ See: safety-[slug]-sds"]
        R6["Rule 6\nSupplier name / S-number\n→ See: supplier-[slug]-directory"]
        R7["Rule 7\nLOW STOCK part + FMEA ref\n→ See: fmea-mXXX-risks"]
    end

    subgraph EXAMPLES["Real Examples from L4 Wiki Pages"]
        A1["maintenance-l4-q3-log\n→ See: fmea-m059-risks"]
        A2["maintenance-l4-q3-log\n→ See: fmea-m072-risks"]
        A3["equipment-m059-specs\n→ See: production-l4-overview"]
        A4["qc-l4-defects-q2\n→ See: maintenance-l4-log"]
        A5["equipment-m059-specs\n→ See: supplier-siemens-industry-inc-directory"]
        A6["safety-chm0024-sds\n→ See: equipment-mXXX-specs\n(chemicals used on machines)"]
        A7["parts-catalog page\n→ See: fmea-mXXX-risks\n(low stock critical part)"]
    end

    R3 -->|"M059 OVERDUE"| A1
    R3 -->|"M072 OVERDUE"| A2
    R2 -->|"L4 mentioned in\nequipment spec"| A3
    R4 -->|"Cpk=0.06\nbelow 1.33"| A4
    R6 -->|"Siemens mentioned\nas supplier"| A5
    R5 -->|"chemical name\nin doc"| A6
    R7 -->|"LOW STOCK part\nreferenced in FMEA"| A7

    style PROMPT_RULES fill:#f3e5f5,stroke:#6A1B9A
    style EXAMPLES fill:#fff8e1,stroke:#E65100
```

---

## Diagram 5 — How a Query Traverses the Wiki

```mermaid
sequenceDiagram
    participant U as User
    participant SP as ANSWER_QUESTION SP
    participant CL as Classifier LLM
    participant CS as Cortex Search (WIKI_INDEX)
    participant WP as WIKI_PAGES
    participant LLM as Synthesis LLM

    U->>SP: "Which L4 machines have overdue\nmaintenance AND Cpk failures?"

    SP->>CL: classify: point_lookup or synthesis?
    CL-->>SP: synthesis

    SP->>CL: what category?
    CL-->>SP: maintenance

    Note over SP: synthesis lane → drop category filter\n(bug fix: search ALL categories)

    SP->>CS: search WIKI_INDEX\n(no category filter, top 8)
    CS-->>SP: maintenance-l4-q3-log ✓\nmaintenance-l2-log ✓\nqc-l2-procedure-summary ✓\nqc-l4-defects-q2 ✓\nproduction-l4-overview ✓\n+ 3 more pages

    SP->>WP: fetch CONTENT_MD\nfor each page_id
    WP-->>SP: full markdown content\n(including → See: cross-refs)

    SP->>LLM: synthesise answer from\ncombined wiki context
    LLM-->>SP: "L2 confirmed: Cpk=0.01 AND\n3 overdue tasks (M100, M068, M037)\nL4: 12 overdue tasks,\nCpk data not in context..."

    SP-->>U: answer + sources array\n+ lane_used + duration_ms
```

---

## Diagram 6 — The page_id Naming Convention

```mermaid
graph LR
    subgraph PATTERN["page_id = category + entity + descriptor"]
        CAT["CATEGORY\n─────────\nequipment\nfmea\nmaintenance\nproduction\nqc\nsafety\nsupplier"]
        ENT["ENTITY\n─────────\nmXXX  machine number\nlX    line number\nchemical slug\nsupplier slug"]
        DESC["DESCRIPTOR\n─────────\nspecs\nrisks\nlog / schedule\noverview\ndefects-qN\nsds\ndirectory"]
    end

    CAT -->|"-"| ENT
    ENT -->|"-"| DESC

    subgraph EXAMPLES2["Real page_ids"]
        E1["equipment-m059-specs"]
        E2["fmea-m072-risks"]
        E3["maintenance-l4-log"]
        E4["production-l4-overview"]
        E5["qc-l4-defects-q2"]
        E6["safety-acetone-sds"]
        E7["supplier-siemens-industry-inc-directory"]
    end

    DESC --> E1
    DESC --> E2
    DESC --> E3
    DESC --> E4
    DESC --> E5
    DESC --> E6
    DESC --> E7

    style PATTERN fill:#e8f5e9,stroke:#2E7D32
    style EXAMPLES2 fill:#e3f2fd,stroke:#1565C0
```

---

## Quick Reference — PDF → Wiki Page → Cross-Ref Target

```
equipment_spec_0008.pdf (M059)
    │
    ├──► equipment-m059-specs        → See: production-l4-overview
    │                                → See: supplier-siemens-industry-inc-directory
    │
    └──► maintenance-m059-schedule   → See: supplier-siemens-industry-inc-directory

maintenance_report_0008.pdf (L4, Q3 2025)
    │
    ├──► maintenance-l4-q3-log       → See: fmea-m059-risks  (M059 OVERDUE)
    │                                → See: fmea-m072-risks  (M072 OVERDUE)
    │
    ├──► maintenance-l4-q3-2025-summary
    │
    └──► production-l4-overview      → See: maintenance-l4-log (Cpk rule)

qc_report_0026.pdf (L4, Q2 2025)
    │
    ├──► qc-l4-defects-q2            → See: maintenance-l4-log (Cpk=0.06 < 1.33)
    │
    └──► production-l4-overview      → See: maintenance-l4-log (shared page)

fmea_worksheet_0050.pdf (M128)
    │
    ├──► fmea-m128-risks             → See: maintenance-l3-log (high RPN)
    │
    └──► equipment-m128-overview     → See: production-l3-overview

safety_data_sheet_0024.pdf (CHM-0024)
    │
    ├──► safety-chm0024-sds
    │
    └──► equipment-chm0024-usage     → See: equipment-mXXX-specs (machine using it)
```
