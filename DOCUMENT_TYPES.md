# Manufacturing Wiki — Document Types Reference

A complete reference for all 7 PDF document types in this dataset, what they contain,
and how they relate to each other.

---

## The Company

This is a **precision engineering / industrial components manufacturer** operating 10 production
lines that each produce a different product type for multiple industrial sectors (automotive,
aerospace, medical devices, and industrial machinery).

### Products by Production Line

| Line | Product Type |
|------|-------------|
| L1   | Precision Gear Assemblies |
| L2   | Structural Aluminium Brackets |
| L3   | Engine Cylinder Heads |
| L4   | Hydraulic Manifold Blocks |
| L5   | Aerospace Titanium Fittings |
| L6   | Automotive Body Stampings |
| L7   | Medical Device Housings |
| L8   | Electronic Enclosures |
| L9   | Power Transmission Shafts |
| L10  | Fluid Control Valve Bodies |

### Shared Universe (seed=42)

All 7 document types share a single consistent universe of entities:

- **200 machines** (M001–M200), each assigned to one production line
- **10 production lines** (L1–L10), each with a supervisor and target throughput
- **20 suppliers** (S001–S020): Haas, Fanuc, SKF, Parker Hannifin, Castrol, Sandvik, etc.
- **50 chemicals** (CHM-0001–CHM-0050): lubricants, coolants, solvents, adhesives
- **30 technicians** (T001–T030): certified specialists across shifts

Every document that references machine M045 is referring to the **same physical machine**
on the **same line** with the **same supplier**. This is what makes cross-document questions possible.

---

## Document Type 1 — Equipment Specification Sheet

**File pattern:** `equipment_spec_NNNN.pdf`
**Scoped to:** One machine (e.g., M045)
**Real-world analogy:** The datasheet you get when you buy a machine tool. Tells you everything
about the machine before you install it.

### Sections

**Cover page**
- Machine ID, model number, manufacturer, production line assignment, bay location
- Serial number, install date, document revision

**1. Technical Specifications** (25 rows)
- Max spindle speed (RPM), number of axes, positional tolerance (mm)
- Power rating (kW), machine weight (kg), coolant capacity (L)
- Tool magazine capacity, rapid traverse speeds X/Y/Z
- Spindle taper type (CAT 40/50, HSK 63A), cutting feed rate
- Table size, axis travel X/Y/Z, noise level dB(A), vibration mm/s²

**2. Component Specifications**
- Spindle Assembly: drive type, bearing type, max torque, encoder resolution
- Control System: controller brand (FANUC 31i-B, Siemens 840D, etc.), memory, program storage
- Coolant System: pump type, tank volume, filtration method, nozzle count
- Chip Conveyor: type (hinge belt / scraper / magnetic), speed, capacity kg/hr

**3. Performance Curves**
- Speed-Torque-Power chart (RPM vs Nm vs kW)
- Shows the machine's operating envelope for roughing vs finishing cuts

**4. Preventive Maintenance Schedule** (20 tasks)
- Daily: check spindle oil, clean chip conveyor, check coolant concentration
- Weekly: lubricate guide ways, check belt tension, verify axis home positions
- Monthly: replace coolant filter, clean ball screws, check spindle runout
- Quarterly: verify axis backlash, replace spindle oil, inspect hydraulic pressure
- Semi-Annual: replace coolant fully, spindle vibration analysis
- Annual: laser calibration, replace drive belts, full electrical safety inspection

**5. Recommended Spare Parts** (up to 180 parts)
- Part numbers, descriptions, quantities, supplier, lead time in days

**6. Installation Requirements**
- Power supply (3-phase 400/480V), compressed air spec, coolant pressure
- Floor load capacity, clearance requirements (front/rear/sides)
- Ambient temperature range, humidity limits, vibration isolation method
- Safety certifications: CE, ISO 16090-1, IEC 60204-1, NFPA 79, UL 508A

### Key relationships
- References `machine.production_line` → links to Production Log and Maintenance Report
- References `machine.supplier_id` → links to Parts Catalog supplier directory
- Recommended Spare Parts list uses same part number format as Parts Catalog
- PM schedule intervals match task types in Maintenance Report task log

---

## Document Type 2 — Parts Catalog

**File pattern:** `parts_catalog_NNNN.pdf`
**Scoped to:** A cluster of 3–5 machines
**Real-world analogy:** The Grainger or RS Components catalog for a specific machine family.
Tells purchasing what to order, at what price, from whom, and how long it will take to arrive.

### Sections

**Cover page**
- Catalog number, which machines are covered (e.g., M012, M045, M078)
- Manufacturer, primary supplier, issue date, revision number, price list effective date

**1. Spend Analysis**
- Pie chart + bar chart: annual spend across 8 categories
- Categories: Bearings, Seals & O-Rings, Belts & Chains, Electrical, Hydraulics, Pneumatics,
  Tooling, Structural
- Table: annual spend ($k), number of part numbers, number of transactions, primary supplier per category

**2. Master Parts List** (up to 250 parts)
Each row:
- Part number (PC-XXXXX), OEM part number, description, category
- Unit of measure (EA/SET/PAIR/M/PKG), list price
- Supplier name, **stock status** (IN STOCK / LOW STOCK / ON ORDER / SOURCED), lead time (days)

Stock status is color-coded: green = IN STOCK, red = LOW STOCK

**3. Approved Supplier Directory**
- 5 suppliers with: code, name, contact, phone, email, lead time, payment terms, rating out of 5

**4. Machine–Part Compatibility Matrix**
- Rows: 8 assemblies (Spindle assy, Ball screw, Linear guide, Servo drive, Tool changer,
  Coolant pump, Chip conveyor, Control unit)
- Columns: 5 machine models
- Values: ✓ compatible, ✗ not compatible, O optional/requires adapter kit

### Key relationships
- Machine IDs in the catalog match machines on a specific production line
- Supplier codes (S001–S020) are the same suppliers in Equipment Spec and Maintenance Report
- Part numbers from this catalog appear in Maintenance Report Parts Replacement Log
- **Critical cross-document link**: A part listed as LOW STOCK here may be the exact part
  flagged as high-RPN in the FMEA Worksheet — the catalog is the only place stock status lives

---

## Document Type 3 — FMEA Worksheet

**File pattern:** `fmea_worksheet_NNNN.pdf`
**Scoped to:** One machine
**Real-world analogy:** The risk register for a machine. Engineers score every possible failure
before it happens so they can prioritise what to fix first.

### FMEA scoring
Each failure mode gets three scores 1–10:
- **S** = Severity (how bad if it fails: 9–10 = safety hazard, 1–2 = negligible)
- **O** = Occurrence (how often it happens: 9–10 = almost certain, 1–2 = remote)
- **D** = Detection (how hard to detect: 9–10 = undetectable, 1–2 = 100% auto-detect)
- **RPN** = S × O × D (Risk Priority Number, max 1000)
  - RPN > 100 = HIGH risk (red)
  - RPN 51–100 = MEDIUM risk (amber)
  - RPN ≤ 50 = LOW risk (green)

### Sections

**Cover page**
- FMEA number, machine ID and model, machine type, production line
- FMEA team lead and members (technician names from T001–T030)
- Total failure modes analysed, count of high-risk (RPN > 100) items

**1. FMEA Scope and Objectives**
- Severity rating scale (table)
- Detection rating scale (table)

**2. RPN Analysis**
- Pareto chart of top-15 failure modes by RPN (bar + cumulative % line)
- Risk scatter matrix (Severity vs Occurrence, color-coded red/amber/green)
- Summary: total modes, high-risk count, max RPN, average RPN

**3. FMEA Worksheet** (48 rows across 12 subsystems)
Subsystems analysed:
- Spindle Assembly: Excessive vibration, Thermal overload, Bearing failure, Runout out of spec
- Axis Drive X/Y/Z: Positional error, Servo alarm, Backlash increase, Drive overload
- Coolant System: Low level, Pump failure, Contaminated coolant, Coolant leak
- Chip Conveyor: Chip jam, Motor overload, Chain breakage, Belt wear
- Tool Changer: Mis-index, Tool drop, ATC arm collision, Slow tool change
- Hydraulic System: Pressure loss, Hydraulic leak, Pump cavitation, Valve sticking
- Electrical Cabinet: Overheating, Ground fault, PLC communication error, Power surge
- Control Unit: Software fault, Memory overflow, Screen failure, Network timeout
- Lubrication System: No lube detected, Line blockage, Pump failure, Empty reservoir
- Pneumatic System: Air pressure drop, Air leak, Valve failure, Filter clogged

Each row: subsystem, failure mode, effect, root cause, S/O/D/RPN scores,
current controls, recommended action, responsible technician, target date,
projected new S/O/D after action (RPN*)

**4. Corrective Action Register**
- All high/medium-priority items with owner, due date, status (OPEN / IN PROGRESS / CLOSED),
  verified by, RPN before and after

### Key relationships
- Machine ID → same machine in Equipment Spec (get full technical specs for context)
- Production line → same line in QC Report (is this failure mode causing the defects we see?)
- Recommended action (e.g., "Replace bearing per PM schedule") → the bearing part number
  must exist in the Parts Catalog — **is it in stock?**
- Technician names are from the same T001–T030 pool as Maintenance Report

---

## Document Type 4 — Maintenance Report

**File pattern:** `maintenance_report_NNNN.pdf`
**Scoped to:** One production line, one quarter
**Real-world analogy:** The quarterly report the maintenance manager presents to operations.
Shows how well the PM program ran, what broke, what was replaced, and what's coming up.

### Sections

**Cover page**
- Report number, period (e.g., Q3 2025-01-01 to 2025-03-31)
- Prepared by / reviewed by (technician names), line supervisor, issue date

**1. Executive Summary + KPI Table**
KPIs tracked:
- Tasks scheduled, tasks completed (target ≥ 85%), tasks deferred (target ≤ 5%), tasks overdue
- Total labour hours, total parts cost ($)
- MTBF (Mean Time Between Failures, hours) — target ≥ 400–800h
- MTTR (Mean Time To Repair, hours) — target ≤ 4–8h
- Status: ON TARGET / BELOW TARGET / ACTION REQ

**2. Task Completion Log** (up to 250 tasks)
14 standard task types:
- Lubricate guide ways, Replace coolant filter, Check spindle oil, Inspect servo cooling
- Verify axis backlash, Clean chip conveyor, Check belt tension, Replace air filter
- Inspect hydraulic seals, Calibrate thermal compensation, Check axis home positions
- Inspect tool changer, Test emergency stop, Update tool offsets

Each task row: Task ID, machine ID, description, scheduled date, completed date,
technician, status (COMPLETED / DEFERRED / OVERDUE), cost ($)

**3. Downtime Analysis**
- Bar chart: per-machine total downtime (hours) for the quarter
- Color: blue < 20h, amber 20–40h, red > 40h. Threshold line at 10h.
- Table per machine: total downtime (hrs), number of events, primary cause, MTBF, MTTR

**4. Parts Replacement Log** (up to 160 parts)
8 part types replaced: spindle bearing, coolant pump seal, air filter, way cover,
ball screw nut, servo drive fuse, coolant hose, control relay
- Part number (RP-XXXXX), description, machine ID, qty, unit cost, total cost, supplier

**5. Upcoming Maintenance Schedule** (next quarter)
- Tasks with priority (HIGH / MEDIUM / LOW), planned date, assigned technician, estimated hours

### Key relationships
- Machine IDs → same machines in Equipment Spec (get PM interval specs) and FMEA (see risk scores)
- Parts Replacement Log part numbers → cross-check with Parts Catalog stock and pricing
- MTBF/MTTR per machine → compare to FMEA's predicted RPN — is the high-RPN machine
  also the one with worst MTBF?
- Tasks OVERDUE in this report → check FMEA to see which failure modes those tasks were preventing
- Supplier in Parts Replacement Log = same supplier in Parts Catalog (lead time, rating)

---

## Document Type 5 — Quality Control Report

**File pattern:** `qc_report_NNNN.pdf`
**Scoped to:** One production line, one quarter
**Real-world analogy:** The quality manager's quarterly report. Shows whether the product
coming off the line meets specification, with statistical evidence.

### Sections

**Cover page**
- Report ID, line ID, supervisor, period, product type, defect threshold %, issue date

**1. KPI Summary**
| KPI | What it measures |
|-----|-----------------|
| Defect Rate (%) | Proportion of defective units, target ≤ threshold (1.2–3.5%) |
| Yield (%) | 100 − defect rate, should be ≥ 96.5–98.8% |
| DPMO | Defects Per Million Opportunities (defect rate × 10,000) |
| Cpk | Process capability index. ≥ 1.33 = capable, < 1.0 = not capable |
| OEE (%) | Overall Equipment Effectiveness, target ≥ 85% |
| Units produced | Raw volume for the quarter |
| Units scrapped | Count of units that could not be reworked |

**2. Defect Rate Trend**
- Daily defect rate line chart over the quarter (90 days)
- Red dashed threshold line
- Summary text: average rate, peak date and value, pass/fail verdict

**3. SPC Control Chart**
- X-bar / R chart for a critical dimension
- Shows UCL, LCL, and centre line
- Reports how many out-of-control points were detected

**4. Defect Detail Log** (up to 350 rows)
9 defect types: Dimensional out-of-spec, Surface finish, Burr/flash, Wrong material,
Assembly error, Marking error, Leak (pressure test), Visual/cosmetic, Weight out-of-spec
8 root causes: Tool wear, Setup error, Raw material, Operator error, Machine drift,
Coolant issue, Program error, Vibration
Each row: date, shift, machine ID, SKU, defect type, count, root cause, action taken

**5. Machine Cpk Summary**
- Per-machine Cpk scores for 3 critical features
- Status: CAPABLE (Cpk ≥ 1.33) / MARGINAL (Cpk 1.0–1.33) / NOT CAPABLE (Cpk < 1.0)

**6. Corrective Action Register**
- CAs with defect category, root cause, action, owner (machine ID), due date, status

### Key relationships
- Production line → same line in Maintenance Report (maintenance gaps cause defects)
- Machine Cpk scores → FMEA for that machine (are low-Cpk machines the same ones with
  high-RPN failure modes?)
- Root cause "Machine drift" → Equipment Spec (is calibration interval adequate?)
- Root cause "Tool wear" → Parts Catalog (are replacement cutting tools in stock?)
- Root cause "Coolant issue" → Safety Data Sheet (is the coolant being used correctly?)
- Defect rate spikes often align with OVERDUE maintenance tasks in the Maintenance Report

---

## Document Type 6 — Production Log

**File pattern:** `production_log_NNNN.pdf`
**Scoped to:** One production line, one week (7 days, 3 shifts per day)
**Real-world analogy:** The shift supervisor's logbook. The most granular operational document —
hour-by-hour record of what every machine produced on every shift.

### Sections

**Cover page**
- Line ID, product type, supervisor, shift manager
- Week start/end dates, total weekly target vs actual units, attainment %

**1. Week Summary**
- One row per shift per day (21 rows = 7 days × 3 shifts)
- Columns: date, shift (Day/Swing/Night), target/shift, actual/shift, attainment %
- Plus: Availability %, Performance %, Quality %, OEE %, Downtime (h)

**2. OEE Analysis**
- Grouped bar chart (Availability / Performance / Quality) with OEE line overlay
- 85% target reference line
- Daily production vs target line chart with red fill showing shortfall

**3. Hourly Production Log** (up to 200 rows)
The most detailed table in the entire dataset. Every hour of every shift:
- Date, hour (00:00–23:00), shift name, machine ID, SKU
- Target units/hr, actual units/hr, scrap count
- Operator name, notes (Tool change / Speed adjustment / Material lot change / etc.)

**4. Downtime Events Register** (up to 100 events)
7 downtime codes:
- PM = Planned Maintenance
- UM = Unplanned Maintenance
- SO = Setup / Changeover
- MT = Material Shortage
- QH = Quality Hold
- BK = Breakdown
- TL = Trial / Testing

Each event: date, start time, end time, duration (h), machine ID, code, description,
technician, status (Resolved / Ongoing / Escalated)

**5. Shift Handover Notes**
- One row per shift: date, shift, supervisor, machines running (count), free-text notes
- Sample notes: "Machine M045 coolant level low — topped up",
  "Bearing noise on M112 — scheduled for PM", "Quality hold on 2 pallets — awaiting QC disposition"

### Key relationships
- OEE in Production Log (weekly, per shift) vs OEE in QC Report (quarterly aggregate)
  — drill down from quarterly trend to a specific bad week
- Downtime events with code BK (Breakdown) → FMEA to see predicted vs actual failures
- Downtime events with code QH (Quality Hold) → QC Report corrective actions
- Hourly scrap counts × weeks → builds up to the quarterly Units Scrapped in QC Report
- Shift handover note "Bearing noise on M112" → FMEA: Bearing failure has RPN = X →
  Parts Catalog: bearing is LOW STOCK → Maintenance Report: PM task is OVERDUE

---

## Document Type 7 — Safety Data Sheet (SDS)

**File pattern:** `safety_data_sheet_NNNN.pdf`
**Scoped to:** One chemical (lubricant, coolant, solvent, or adhesive)
**Standard:** GHS / OSHA HazCom 2012 (16 sections)
**Real-world analogy:** The mandatory regulatory document that must accompany every
hazardous substance. Required by law for storage, handling, and emergency response.

### The 16 Sections

| # | Title | Key Content |
|---|-------|-------------|
| 1 | Identification | Product name, CAS number, chemical family, hazard class, intended use, emergency phone |
| 2 | Hazard Identification | GHS signal word (DANGER/WARNING), hazard statements (H-codes), precautionary statements (P-codes) |
| 3 | Composition | 2–5 components with CAS numbers, concentration %, EC numbers, GHS classification |
| 4 | First Aid Measures | Eye/skin/inhalation/ingestion procedures, notes to physician |
| 5 | Firefighting | Flash point, auto-ignition temp, explosive limits (LEL/UEL), extinguishing media, PPE for firefighters |
| 6 | Accidental Release | Spill response, containment, disposal, regulatory reporting |
| 7 | Handling and Storage | Ventilation requirements, storage temperature, incompatibilities |
| 8 | Exposure Controls / PPE | OSHA PEL, ACGIH TLV-TWA/STEL, engineering controls, respiratory/hand/eye/body protection required. Includes TLV exposure chart. |
| 9 | Physical/Chemical Properties | Appearance, odour, pH, melting/boiling point, vapour pressure, density, solubility, viscosity |
| 10 | Stability and Reactivity | Conditions to avoid, incompatible materials, hazardous decomposition products |
| 11 | Toxicological Information | LD50 (oral/dermal), LC50 (inhalation), skin sensitisation, mutagenicity, carcinogenicity, STOT |
| 12 | Ecological Information | Aquatic toxicity (fish/daphnia/algae), biodegradability, bioaccumulation factor |
| 13 | Disposal | Waste disposal method, EWC waste code |
| 14 | Transport | UN number, proper shipping name, hazard class, packing group, marine pollutant flag |
| 15 | Regulatory Information | SARA 311/312, TSCA status, REACH registration, EU classification, California Prop 65 |
| 16 | Other Information | Prepared by, issue date, supersedes date, disclaimer |

### Key relationships
- Chemical SKU (CHM-0001–CHM-0050) → same chemical referenced in Equipment Spec
  (coolant system type, lubrication system spec)
- PPE required in Section 8 → cross-check Maintenance Report to ensure technicians
  performing coolant replacement are wearing correct PPE
- Flash point in Section 5 → affects storage rules in the facility
- Section 7 storage temperature → if the coolant is stored above max temp, it degrades →
  root cause of "Coolant issue" defects in QC Report
- Chemical supplier → same S001–S020 supplier pool as Parts Catalog

---

## How All 7 Documents Relate

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              SHARED UNIVERSE (seed=42)                   │
                    │  200 machines · 10 lines · 20 suppliers · 50 chemicals   │
                    └─────────────────────────────────────────────────────────┘
                                           │
          ┌──────────┬────────────┬────────┼──────────┬────────────┬─────────┐
          ▼          ▼            ▼        ▼          ▼            ▼         ▼
     Equipment    Parts       FMEA    Maintenance   QC         Production  Safety
       Spec      Catalog    Worksheet   Report     Report        Log       Data
                                                                           Sheet
     (1 machine) (3-5 mach) (1 mach)  (1 line,   (1 line,    (1 line,   (1 chem)
                                       1 quarter)  1 quarter)   1 week)
```

### The Three Types of Cross-Document Questions

**Type A — Machine deep-dive** (Equipment Spec + FMEA + Maintenance Report + Parts Catalog)
> "Machine M045 has a high-RPN bearing failure. Is the bearing in stock? When was it last serviced?"
- Equipment Spec → bearing type and PM interval
- FMEA → RPN score and recommended action
- Maintenance Report → last completed bearing service task, any OVERDUE tasks
- Parts Catalog → current stock status and lead time for that bearing

**Type B — Line performance** (Production Log + QC Report + Maintenance Report)
> "Why did Line L3 miss its production target in Q1? Is there a quality or maintenance link?"
- Production Log → which shifts missed target, which machines had downtime, what codes
- QC Report → defect rate that week, which machines had low Cpk, root causes
- Maintenance Report → any OVERDUE PM tasks that quarter, downtime hours per machine

**Type C — Chemical safety** (Safety Data Sheet + Equipment Spec + Maintenance Report)
> "What PPE do technicians need when replacing the coolant on M045, and how often is it replaced?"
- Equipment Spec → which coolant type is used on M045, coolant capacity, semi-annual replacement task
- Safety Data Sheet → PPE requirements for that specific coolant (respirator, gloves, eye protection)
- Maintenance Report → when was the last full coolant replacement, is it overdue?

---

## Example: The Full Chain for a Single Problem

**Scenario:** Line L3 is producing Engine Cylinder Heads with a rising defect rate.

```
Step 1 — QC Report (L3, Q3)
  Cpk for M067 Feature 2 = 0.91 → NOT CAPABLE
  Root cause logged: "Machine drift"

Step 2 — FMEA Worksheet (M067)
  Axis Drive Z: "Positional error" → RPN = 504 (S=7, O=8, D=9)
  Recommended action: "Tighten servo tuning parameters"
  Status: OPEN

Step 3 — Maintenance Report (L3, Q3)
  Task T298741 — "Verify axis backlash" on M067 → OVERDUE
  MTBF for M067 = 312h (target ≥ 500h)

Step 4 — Equipment Spec (M067)
  Quarterly PM: "Verify axis backlash — 60 min, Ball bar software"
  Last calibration: over 6 months ago

Step 5 — Parts Catalog (covers M067)
  Ball screw nut OEM-XXXXX → ON ORDER, lead time: 28 days

Step 6 — Production Log (L3, Week 32)
  Shift handover note: "Dimensional variation on M067 Z-axis — adjusted manually"
  Hourly scrap for M067: 3–5 units/hr above baseline
```

**The answer to "why is L3 defect rate rising?" requires all 6 document types.**
No single document contains it. This is exactly why the Karpathy wiki approach exists —
the wiki compilation step reads all documents and builds the cross-reference links so the
synthesis lane can answer it in one query.
