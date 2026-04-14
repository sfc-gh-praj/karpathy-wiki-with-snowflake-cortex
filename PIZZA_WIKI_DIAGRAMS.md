# PDF Relationships — Pizza Restaurant Edition

All diagrams use Mermaid. Render at https://mermaid.live or in VS Code / GitHub.

---

## Diagram 1 — The Pizza Restaurant and Its 7 Report Types

```mermaid
graph TD
    subgraph RESTAURANT["🍕 The Pizza Restaurant (= The Factory)"]
        STATION["Kitchen Station\ne.g. Pizza Station\n= Production Line L4"]
        OVEN["Individual Equipment\ne.g. Oven #3, Mixer #1\n= Machine M059"]
        CHEM["Cleaning Chemical\ne.g. EZ-Klean Degreaser\n= Chemical CHM-0024"]
        SUP["Parts Supplier\ne.g. Welbilt Inc.\n= Supplier S007"]
    end

    subgraph PDFS["📄 The 7 Report Types"]
        ES["📋 Equipment Spec\nThe manual that came\nwith Oven #3\n─────────────\nMax temp, power,\nweight, daily checks,\nannual calibration"]

        PC["🛒 Parts Catalog\nSpare parts you can\norder for the ovens\n─────────────\nHeating elements,\ndoor seals, motors\nwith stock levels"]

        FM["⚠️ FMEA Worksheet\nRisk assessment:\nwhat could go wrong\nwith Oven #3?\n─────────────\nRPN = Severity\n× Occurrence\n× Detection"]

        MR["🔧 Maintenance Report\nMonthly inspection log\nfor the whole Pizza Station\n─────────────\nWhat got serviced,\nwhat was skipped,\nwhat is OVERDUE"]

        QC["📊 QC Report\nQuality inspector report\nfor the Pizza Station\n─────────────\nHow many pizzas rejected,\nare sizes consistent?\nCpk score"]

        PL["📈 Production Log\nHour-by-hour output\nfor one week\n─────────────\nHow many pizzas made,\nwhat stopped the line,\nOEE score"]

        SD["🧪 Safety Data Sheet\nSafety info for\nEZ-Klean Degreaser\n─────────────\nHazards, PPE needed,\nstorage rules,\ndisposal method"]
    end

    OVEN -->|"described by"| ES
    OVEN -->|"described by"| FM
    OVEN -->|"described by"| PC
    STATION -->|"described by"| MR
    STATION -->|"described by"| QC
    STATION -->|"described by"| PL
    CHEM  -->|"described by"| SD

    style RESTAURANT fill:#fff8e1,stroke:#FF9800,color:#000
    style PDFS fill:#e3f2fd,stroke:#1565C0,color:#000
```

---

## Diagram 2 — How a PDF Becomes a Wiki Page (The Domain Prompt Pipeline)

```mermaid
flowchart TD
    subgraph PDFS2["📄 Raw PDFs on Snowflake Stage"]
        P1["equipment_spec_oven3.pdf\nOven #3 manual"]
        P2["maintenance_report_pizza_station.pdf\nPizza Station, Oct 2025"]
        P3["qc_report_pizza_station.pdf\nPizza Station, Q3 2025"]
        P4["fmea_oven3.pdf\nOven #3 risk assessment"]
        P5["safety_ezklean.pdf\nEZ-Klean Degreaser SDS"]
    end

    subgraph PROMPT["📋 Domain Prompt\n(stored in PROMPT_REGISTRY)"]
        DP["Instructions to the AI:\n══════════════════\n✏️ CONTENT RULES\n• Write exactly 2 wiki cards\n• Max 200 words each\n• Card 1 = what IS this thing?\n• Card 2 = what do you DO with it?\n• Mark OVERDUE tasks with ALERT:\n• Mark Cpk below 1.33 with ALERT:\n• Always include IDs and units\n══════════════════\n🔗 CROSS-REFERENCE RULES\n• Oven number mentioned\n  → link to its spec card\n• Station name mentioned\n  → link to station overview\n• OVERDUE task found\n  → link to risk card\n• Cpk below 1.33 found\n  → link to maintenance log\n• Chemical mentioned\n  → link to safety sheet\n• Supplier mentioned\n  → link to supplier card"]
    end

    subgraph AI["🤖 AI reads both together"]
        STEP1["① Extract raw text from PDF"]
        STEP2["② Fetch domain prompt\nfrom PROMPT_REGISTRY"]
        STEP3["③ AI reads: domain prompt\n+ raw PDF text\nand writes 2 wiki cards as JSON"]
        STEP4["④ Save cards to\nWIKI_PAGES table"]
    end

    subgraph CARDS["📚 Wiki Cards Created\n(rows in WIKI_PAGES table)"]
        W1["🔴 equipment-oven3-specs\nOven #3 — Blodgett-1048\nMax 600°F, 12kW, Bay-02\n→ See: station-pizza-overview\n→ See: supplier-welbilt-directory"]

        W2["🟠 maintenance-oven3-schedule\nOven #3 PM Schedule\nDaily: check door seal 5min\nMonthly: clean grease trap\nAnnual: recalibrate sensors 4hr"]

        W3["🟡 maintenance-pizza-station-log\nALERT: Oven #3 grease trap\nOVERDUE since Sept 15\nALERT: Mixer #1 belt OVERDUE\n→ See: fmea-oven3-risks\n→ See: fmea-mixer1-risks"]

        W4["🟢 station-pizza-overview\nPizza Station overview\nOEE 81.4% ALERT below 85%\nCpk 0.06 ALERT below 1.33\n→ See: maintenance-pizza-station-log"]

        W5["🔵 qc-pizza-station-q3\nALERT: Cpk = 0.06\n3.04% pizzas rejected\nOven #3 flagged most often\n→ See: maintenance-pizza-station-log"]

        W6["🟣 fmea-oven3-risks\nALERT: Grease trap blockage\nRPN 480 (S=8, O=6, D=10)\nEffect: uneven heat → raw pizza\nAction: install temp alarm"]

        W7["⚫ safety-ezklean-sds\nEZ-Klean Degreaser\nHazard: corrosive\nPPE: gloves + goggles\nStorage: below 25°C"]
    end

    P1 --> STEP1
    P2 --> STEP1
    P3 --> STEP1
    P4 --> STEP1
    P5 --> STEP1
    STEP1 --> STEP2
    DP --> STEP2
    STEP2 --> STEP3
    STEP3 --> STEP4
    STEP4 --> W1
    STEP4 --> W2
    STEP4 --> W3
    STEP4 --> W4
    STEP4 --> W5
    STEP4 --> W6
    STEP4 --> W7

    style PDFS2 fill:#e3f2fd,stroke:#1565C0,color:#000
    style PROMPT fill:#f3e5f5,stroke:#6A1B9A,color:#000
    style AI fill:#e8f5e9,stroke:#2E7D32,color:#000
    style CARDS fill:#fff8e1,stroke:#E65100,color:#000
```

---

## Diagram 3 — The Cross-Reference Web (Pizza Story)

This is the full chain: bad pizzas → find the root cause across 5 different PDFs.
Every arrow is a `→ See:` link written into the wiki card by the domain prompt.

```mermaid
graph TD
    subgraph QC_BOX["📊 From: qc_report_pizza_station.pdf"]
        Q1["qc-pizza-station-q3\n─────────────\nALERT: Cpk = 0.06\nUndercooked pizzas: 14 incidents\nOven #3 flagged most often"]
    end

    subgraph MAINT_BOX["🔧 From: maintenance_report_pizza_station.pdf"]
        M1["maintenance-pizza-station-log\n─────────────\nALERT: Oven #3 grease trap\nOVERDUE 75 days (due every 30)\nALERT: Mixer #1 belt OVERDUE\n23 tasks deferred to next month"]
    end

    subgraph FMEA_BOX["⚠️ From: fmea_oven3.pdf"]
        F1["fmea-oven3-risks\n─────────────\nALERT: Grease trap blockage\nRPN 480 — CRITICAL\nEffect: raw / undercooked pizzas\nAction: install temp variance alarm"]
    end

    subgraph EQUIP_BOX["📋 From: equipment_spec_oven3.pdf"]
        E1["equipment-oven3-specs\n─────────────\nOven #3 — Blodgett-1048\nMax 600°F, 12kW\nGrease trap: clean every 30 days\nLocation: Pizza Station, Bay-02"]
        E2["maintenance-oven3-schedule\n─────────────\nDaily: check door seal 5 min\nMonthly: clean grease trap\nAnnual: full electrical check 3hr\nCritical spare: heating element\n58-day lead time"]
    end

    subgraph PARTS_BOX["🛒 From: parts_catalog.pdf"]
        P1["parts-pizza-station-catalog\n─────────────\nHeating element: IN STOCK 12 units\nDoor seal gasket: LOW STOCK 1 unit\nGrease filter: LOW STOCK 0 units\nTemp sensor: ON ORDER"]
    end

    subgraph SAFETY_BOX["🧪 From: safety_ezklean.pdf"]
        S1["safety-ezklean-sds\n─────────────\nEZ-Klean Degreaser\nHazard: corrosive\nPPE: nitrile gloves + goggles\nNeeded to: clean grease trap"]
    end

    subgraph SUPPLIER_BOX["🏢 Supplier"]
        SUP["supplier-welbilt-directory\n─────────────\nWelbilt Inc.\nContact: parts@welbilt.com\nLead times: 3–58 days"]
    end

    Q1  -->|"ALERT: Cpk=0.06\nCross-ref rule 4:\nCpk below 1.33\n→ check maintenance log"| M1

    M1  -->|"ALERT: Oven #3 OVERDUE\nCross-ref rule 3:\nOVERDUE task found\n→ check risk card"| F1

    F1  -->|"Oven #3 mentioned\nCross-ref rule 1:\nequipment ID found\n→ check spec card"| E1

    E1  -->|"Welbilt supplier mentioned\nCross-ref rule 6:\nsupplier mentioned\n→ check supplier card"| SUP

    P1  -->|"LOW STOCK grease filter\n+ FMEA references grease trap\nCross-ref rule 7:\nlow stock + FMEA ref\n→ check risk card"| F1

    E2  -->|"EZ-Klean needed\nfor grease trap cleaning\nCross-ref rule 5:\nchemical mentioned\n→ check safety sheet"| S1

    style QC_BOX fill:#fff8e1,stroke:#F57F17,color:#000
    style MAINT_BOX fill:#e8f5e9,stroke:#1B5E20,color:#000
    style FMEA_BOX fill:#ffebee,stroke:#B71C1C,color:#000
    style EQUIP_BOX fill:#e3f2fd,stroke:#0D47A1,color:#000
    style PARTS_BOX fill:#f3e5f5,stroke:#4A148C,color:#000
    style SAFETY_BOX fill:#fce4ec,stroke:#880E4F,color:#000
    style SUPPLIER_BOX fill:#e0f2f1,stroke:#004D40,color:#000
```

---

## Diagram 4 — Domain Prompt Rules in Pizza Language

Each rule in the domain prompt creates one type of arrow in the wiki.

```mermaid
graph LR
    subgraph RULES["📋 Domain Prompt Cross-Reference Rules\n(pizza language)"]
        R1["Rule 1: Oven number mentioned\n→ link to its spec card\nequipment-ovenX-specs"]
        R2["Rule 2: Station name mentioned\n→ link to station overview\nstation-pizza-overview"]
        R3["Rule 3: OVERDUE task found\nin a maintenance report\n→ link to that oven's risk card\nfmea-ovenX-risks"]
        R4["Rule 4: Cpk below 1.33 found\nin a QC report\n→ link to the maintenance log\nmaintenance-pizza-station-log"]
        R5["Rule 5: Cleaning chemical mentioned\n→ link to its safety sheet\nsafety-ezklean-sds"]
        R6["Rule 6: Supplier name mentioned\n→ link to supplier card\nsupplier-welbilt-directory"]
        R7["Rule 7: Spare part LOW STOCK\nand referenced in FMEA\n→ link to that oven's risk card\nfmea-ovenX-risks"]
    end

    subgraph ARROWS["🔗 The arrows it creates in the wiki"]
        A1["maintenance log\n→ See: fmea-oven3-risks\n(Oven #3 grease trap overdue)"]
        A2["equipment spec\n→ See: station-pizza-overview\n(Pizza Station mentioned)"]
        A3["maintenance log\n→ See: fmea-mixer1-risks\n(Mixer #1 belt overdue)"]
        A4["qc report\n→ See: maintenance-pizza-station-log\n(Cpk = 0.06)"]
        A5["oven PM schedule\n→ See: safety-ezklean-sds\n(degreaser mentioned)"]
        A6["equipment spec\n→ See: supplier-welbilt-directory\n(Welbilt Inc. mentioned)"]
        A7["parts catalog\n→ See: fmea-oven3-risks\n(grease filter LOW STOCK)"]
    end

    R3 -->|"fires when"| A1
    R3 -->|"fires when"| A3
    R2 -->|"fires when"| A2
    R4 -->|"fires when"| A4
    R5 -->|"fires when"| A5
    R6 -->|"fires when"| A6
    R7 -->|"fires when"| A7

    style RULES fill:#f3e5f5,stroke:#6A1B9A,color:#000
    style ARROWS fill:#e8f5e9,stroke:#2E7D32,color:#000
```

---

## Diagram 5 — Asking the Wiki a Question (Pizza Version)

```mermaid
sequenceDiagram
    participant YOU as 👤 You
    participant SP as ⚙️ ANSWER_QUESTION
    participant CL as 🧠 Classifier AI
    participant CS as 🔍 Search<br/>(WIKI_INDEX)
    participant WP as 📚 WIKI_PAGES
    participant AI as 🤖 Answer AI

    YOU->>SP: "Why are pizzas coming out<br/>undercooked on the Pizza Station<br/>and which ovens need maintenance?"

    SP->>CL: Is this a simple lookup<br/>or does it need multiple sources?
    CL-->>SP: synthesis<br/>(needs multiple wiki cards)

    Note over SP: synthesis = search ALL categories<br/>no filter — we need QC + maintenance<br/>+ FMEA cards together

    SP->>CS: Search wiki index<br/>for relevant cards (top 8)
    CS-->>SP: ✅ qc-pizza-station-q3<br/>✅ maintenance-pizza-station-log<br/>✅ fmea-oven3-risks<br/>✅ equipment-oven3-specs<br/>✅ station-pizza-overview<br/>+ 3 more cards

    SP->>WP: Get full content<br/>of each card
    WP-->>SP: Full markdown text<br/>including all → See: cross-refs

    SP->>AI: Here are 8 wiki cards.<br/>Answer the question using only<br/>this information.
    AI-->>SP: "ALERT: Oven #3 grease trap is<br/>75 days overdue (should be 30 days).<br/>FMEA shows this causes uneven heat<br/>→ undercooked pizzas. RPN=480 critical.<br/>Also Mixer #1 belt overdue.<br/>→ See: fmea-oven3-risks for full risk list."

    SP-->>YOU: Answer + list of sources used<br/>+ how long it took
```

---

## Diagram 6 — How Wiki Card Names Are Built (Pizza Version)

Every card has a name built from 3 parts so that cross-references always match.

```mermaid
graph LR
    subgraph PARTS["Card name = category + equipment-or-station + what-aspect"]
        C["CATEGORY\n──────────\nequipment\nfmea\nmaintenance\nstation\nqc\nsafety\nsupplier"]
        E["ENTITY\n──────────\noven3  ← oven number\nmixer1 ← mixer number\npizza-station ← station name\nezklean ← chemical slug\nwelbilt ← supplier slug"]
        D["DESCRIPTOR\n──────────\nspecs ← technical details\nrisks ← FMEA risk list\nlog   ← maintenance log\nschedule ← PM schedule\noverview ← station summary\nsds  ← safety data sheet\ndirectory ← supplier info"]
    end

    C -->|" - "| E
    E -->|" - "| D

    subgraph EXAMPLES["Real card names (page_ids)"]
        X1["equipment-oven3-specs\n'the spec card for Oven #3'"]
        X2["fmea-oven3-risks\n'the risk card for Oven #3'"]
        X3["maintenance-oven3-schedule\n'the PM schedule for Oven #3'"]
        X4["maintenance-pizza-station-log\n'the maintenance log for Pizza Station'"]
        X5["qc-pizza-station-q3\n'the Q3 quality report for Pizza Station'"]
        X6["safety-ezklean-sds\n'the safety sheet for EZ-Klean'"]
        X7["supplier-welbilt-directory\n'the Welbilt supplier card'"]
    end

    D --> X1
    D --> X2
    D --> X3
    D --> X4
    D --> X5
    D --> X6
    D --> X7

    style PARTS fill:#e8f5e9,stroke:#2E7D32,color:#000
    style EXAMPLES fill:#e3f2fd,stroke:#1565C0,color:#000
```

---

## The Complete Pizza Story in One Picture

```
THE PROBLEM: Customers are complaining about undercooked pizzas.

┌─────────────────────────────────────────────────────────────────────┐
│  📊 QC Report (qc_report_pizza_station.pdf)                         │
│                                                                     │
│  ALERT: Cpk = 0.06  ← pizzas are wildly inconsistent in size/cook  │
│  14 undercooked incidents this month                                │
│  Oven #3 flagged most often                                         │
│                        │                                            │
│         Cross-ref rule 4: Cpk below 1.33                           │
│         → See: maintenance-pizza-station-log ──────────────────┐   │
└─────────────────────────────────────────────────────────────────│───┘
                                                                  │
┌─────────────────────────────────────────────────────────────────▼───┐
│  🔧 Maintenance Report (maintenance_report_pizza_station.pdf)        │
│                                                                     │
│  ALERT: Oven #3 grease trap OVERDUE — 75 days (should be 30 days)  │
│  ALERT: Mixer #1 belt OVERDUE — 47 days                             │
│                        │                                            │
│         Cross-ref rule 3: OVERDUE task found                       │
│         → See: fmea-oven3-risks ───────────────────────────────┐   │
└─────────────────────────────────────────────────────────────────│───┘
                                                                  │
┌─────────────────────────────────────────────────────────────────▼───┐
│  ⚠️ FMEA Worksheet (fmea_oven3.pdf)                                  │
│                                                                     │
│  Grease trap blockage: RPN = 480 ← CRITICAL (threshold is 100)     │
│  Severity=8, Occurrence=6, Detection=10                             │
│  Effect: uneven heat distribution → raw / undercooked pizzas        │
│  Recommended action: install temperature variance alarm             │
│                        │                                            │
│         Cross-ref rule 1: Oven #3 mentioned                        │
│         → See: equipment-oven3-specs ──────────────────────────┐   │
└─────────────────────────────────────────────────────────────────│───┘
                                                                  │
┌─────────────────────────────────────────────────────────────────▼───┐
│  📋 Equipment Spec (equipment_spec_oven3.pdf)                        │
│                                                                     │
│  Oven #3 — Blodgett-1048                                            │
│  Grease trap: MUST be cleaned every 30 days ← last done 75 days ago │
│  Supplier: Welbilt Inc.                                             │
│  Uses: EZ-Klean Degreaser for grease trap cleaning                  │
│          │                          │                               │
│  rule 6: supplier      rule 5: chemical mentioned                   │
│  → See: supplier-      → See: safety-ezklean-sds                   │
│    welbilt-directory         │                                      │
└──────────────────────────────│──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│  🧪 Safety Data Sheet (safety_ezklean.pdf)                           │
│                                                                     │
│  EZ-Klean Industrial Degreaser                                      │
│  ⚠️  Corrosive — causes skin burns                                   │
│  PPE required: nitrile gloves + safety goggles + apron             │
│  Storage: below 25°C, away from food                               │
│  Tell the maintenance team before they start cleaning Oven #3!      │
└─────────────────────────────────────────────────────────────────────┘

ALSO CHECK:
┌─────────────────────────────────────────────────────────────────────┐
│  🛒 Parts Catalog                                                    │
│                                                                     │
│  Grease trap filter: LOW STOCK — 0 units left                      │
│  (cross-ref rule 7: LOW STOCK + FMEA references grease trap)        │
│  → See: fmea-oven3-risks                                            │
│  Order immediately — 14-day lead time!                              │
└─────────────────────────────────────────────────────────────────────┘

ROOT CAUSE FOUND: Oven #3 grease trap not cleaned for 75 days.
NEXT STEPS:
  1. Order grease trap filters (0 in stock, 14-day lead)
  2. Get PPE (gloves + goggles per safety sheet)
  3. Clean the grease trap
  4. Install temperature variance alarm (per FMEA recommendation)
```
