# Understanding the Wiki — No Manufacturing Knowledge Required

Forget factories. Think pizza restaurant.

---

## The Pizza Restaurant = The Factory

Imagine a large pizza restaurant with multiple kitchen stations,
each with several pieces of equipment, a team of chefs, and a manager.

| Pizza Restaurant | Factory Term | ID Format |
|-----------------|-------------|-----------|
| The whole restaurant | The factory | — |
| A kitchen station (pizza, pasta, grill) | Production line | L1–L10 |
| One piece of equipment (oven #1, mixer #2) | Machine | M001–M200 |
| A chef / technician | Technician | T001–T030 |
| A cleaning chemical (oven cleaner, degreaser) | Chemical | CHM-0001–CHM-0050 |
| A supplier (the company you buy spare parts from) | Supplier | S001–S020 |

The factory makes **precision metal parts** the same way a restaurant makes pizzas —
raw materials go in one end, finished products come out the other,
and the machines (ovens) do the work.

---

## The 7 PDF Types — In Pizza Language

### PDF 1 — Equipment Spec
**Pizza version**: The manual that came in the box when you bought Oven #3.

```
Oven #3 (Model: Blodgett-1048)
- Max temperature: 600°F
- Power: 12kW
- Weight: 180kg
- Located: Pizza station, Bay-02
- Supplier: Welbilt Inc.
- Installed: 2019-11-12
- Daily check: inspect door seal, check thermostat
- Annual: recalibrate temperature sensors (takes 4 hours)
```

In the factory: same thing but for a CNC machine or a laser cutter.

---

### PDF 2 — Parts Catalog
**Pizza version**: The spare parts catalog for your ovens.
When the heating element in Oven #3 burns out, you order from this catalog.

```
Heating Elements:    Part SP-394, $85 each, 14-day lead time  — IN STOCK (12 units)
Door Seal Gaskets:   Part SP-102, $22 each,  3-day lead time  — LOW STOCK (1 unit) ⚠️
Thermostat Sensors:  Part SP-771, $140 each, 30-day lead time — ON ORDER
```

The LOW STOCK flag is important — if the only door seal breaks and
you have none in stock, the oven is down and no pizzas get made.

---

### PDF 3 — FMEA Worksheet
**Pizza version**: A risk assessment someone did on Oven #3.
"What could go wrong, how bad would it be, and how likely is it?"

FMEA = Failure Mode and Effects Analysis. Every failure gets a score:

```
RPN = Severity (1–10) × Occurrence (1–10) × Detection (1–10)
```

Higher RPN = more dangerous / urgent to fix.

```
Failure: Heating element burnout
  Severity:   8  (pizza comes out raw — food safety issue)
  Occurrence: 6  (happens a few times a year)
  Detection:  4  (temperature alarm usually catches it)
  RPN = 8 × 6 × 4 = 192  ← ALERT: above threshold of 100

Failure: Door hinge stiff
  Severity:   2  (annoying but pizza still cooks)
  Occurrence: 9  (happens constantly)
  Detection:  1  (you see it immediately)
  RPN = 2 × 9 × 1 = 18  ← low priority
```

The FMEA tells you: **if this machine breaks, how serious is it?**

---

### PDF 4 — Maintenance Report
**Pizza version**: The monthly inspection report for the entire Pizza Station.

```
Pizza Station — October 2025
Prepared by: Head Chef Maria

OVERDUE TASKS ⚠️:
  Oven #3:  Clean grease trap  (was due Sept 15th, still not done)
  Mixer #1: Replace drive belt  (was due Sept 28th, still not done)

COMPLETED THIS MONTH:
  Oven #1:  Thermostat calibration ✓
  Oven #2:  Door seal replaced ✓

DEFERRED (scheduled but pushed back):
  23 tasks pushed to next month

DOWNTIME THIS MONTH:
  Oven #3 down 4 hours (belt snapped)
  Total downtime: 4.2% of operating hours
```

The maintenance report covers the **whole station (production line)** for **one quarter**.
It tells you: **what was supposed to be done, what got done, and what was skipped.**

---

### PDF 5 — QC Report
**Pizza version**: The quality inspector's monthly report on Pizza Station output.

```
Pizza Station — Q3 2025 Quality Report

Total pizzas made:    7,165
Total rejected:       218 (3.04%) — target ≤ 3.2% ✓
Customer complaints:  12

ALERT: Process Capability Cpk = 0.06
  (target ≥ 1.33 — this means the process is wildly inconsistent)
  Translation: our pizza sizes are all over the place.
  Some are 8 inches, some are 14 inches, target is 12 inches.

Top defect types:
  Undercooked:          14 incidents  ← probably Oven #3 (has overdue grease trap)
  Wrong toppings:       11 incidents  ← operator error
  Burnt edges:          10 incidents  ← oven running too hot
```

**Cpk** is the key number. Cpk ≥ 1.33 means the process is consistent and controlled.
Cpk = 0.06 means it's chaos — the output is unpredictable.

The QC Report covers the **whole station** for **one quarter**.
It tells you: **how good is what we're making?**

---

### PDF 6 — Production Log
**Pizza version**: The hour-by-hour output log for one week.

```
Pizza Station — Week of Oct 7–13, 2025

Monday:
  09:00–10:00: 42 pizzas  ✓
  10:00–11:00: 38 pizzas  ✓
  11:00–12:00: 0 pizzas   ← Oven #3 down (belt snapped)
  ...

OEE (Overall Equipment Effectiveness): 81.4%
  Target: ≥ 85%  ← BELOW TARGET ⚠️
  Translation: our ovens are only useful 81% of the time they should be running.

Downtime events:
  10:55 — Oven #3 belt failure, 55 min repair
  14:30 — Mixer #1 jam, 12 min clear
```

**OEE** is the health score of the station.
100% = running perfectly all the time. 81% = something keeps going wrong.

The Production Log covers the **whole station** for **one week**.
It tells you: **how much did we make and what stopped us?**

---

### PDF 7 — Safety Data Sheet (SDS)
**Pizza version**: The safety information card for your industrial oven cleaner.

```
Product: EZ-Klean Industrial Degreaser (CHM-0024)

HAZARDS: Corrosive. Causes skin burns. Vapours irritate lungs.

FIRST AID:
  Skin contact: flush with water 15 minutes
  Eye contact:  flush with water, call doctor immediately
  Inhaled:      move to fresh air

STORAGE: Store below 25°C, away from heat sources.
         Do not store near food products.

PPE REQUIRED: Nitrile gloves, safety goggles, apron.

DISPOSAL: Do not pour down drain. Contact hazardous waste contractor.
```

Every chemical in the building has one. 16 standard sections (GHS format).

---

## How the 7 PDFs Connect — The Pizza Station Story

Here is why all 7 PDFs are related. They all describe the **same station, the same ovens**.

```
You notice: Pizza quality is dropping. More undercooked pizzas than last month.

Step 1 — Check the QC Report (PDF 5)
  → ALERT: Cpk = 0.06 on Pizza Station. Oven #3 flagged most often.
  → "The process is inconsistent. Oven #3 is the likely culprit."
  → Cross-ref: → See: maintenance-pizza-station-log

Step 2 — Check the Maintenance Report (PDF 4)
  → ALERT: Oven #3 grease trap cleaning OVERDUE since Sept 15th.
  → "A clogged grease trap causes uneven heat distribution — that's why pizzas cook unevenly."
  → Cross-ref: → See: fmea-oven3-risks

Step 3 — Check the FMEA Worksheet (PDF 3)
  → "Grease trap blockage" failure mode: RPN = 480 (CRITICAL)
  → Effect: Uneven temperature → undercooked pizzas → food safety risk
  → Recommended action: Install temperature variance alarm
  → "This was flagged as high risk months ago. The overdue maintenance is now causing it."

Step 4 — Check the Equipment Spec (PDF 1)
  → Oven #3 grease trap: should be cleaned every 30 days.
  → Last cleaned: 75 days ago.
  → "The spec says 30 days. It's been 75. There's your answer."

Step 5 — Check the Parts Catalog (PDF 2)
  → Grease trap filter: LOW STOCK — only 1 unit left.
  → "We can do the maintenance, but we'll have no spare. Order more immediately."

Step 6 — Check the Safety Data Sheet (PDF 7)
  → The degreaser used to clean the grease trap: requires nitrile gloves + goggles.
  → Storage: keep below 25°C.
  → "Make sure the maintenance team has the right PPE before they start."

Step 7 — Check the Production Log (PDF 6)
  → Oven #3 was down 55 minutes on Monday.
  → OEE dropped to 81.4% — 3.6 points below target.
  → "The downtime is already showing up in the weekly output numbers."
```

**All 7 PDFs told one story:**
> Oven #3's grease trap is overdue for cleaning → causing uneven heat → causing undercooked pizzas → dragging down Cpk and OEE.

---

## Now Map Back to the Factory

The factory is just a bigger, more expensive version of the same thing.
Instead of pizza ovens, the machines are laser cutters and CNC mills.
Instead of pizza quality, the QC metric is dimensional tolerance (is the metal part the right size?).

| Pizza Version | Factory Version |
|--------------|----------------|
| Pizza Station | Production Line L4 |
| Oven #3 | Machine M059 (Laser Cutter) |
| Grease trap overdue | Chip conveyor cleaning overdue |
| Undercooked pizzas | Dimensional out-of-spec parts |
| Cpk = 0.06 (sizes inconsistent) | Cpk = 0.06 (part dimensions inconsistent) |
| OEE = 81.4% | OEE = 81.4% |
| Industrial degreaser | Metalworking coolant (CHM-0024) |
| Welbilt Inc. (oven supplier) | Siemens Industry Inc. (machine supplier) |

The numbers, the alerts, the cross-references — all identical. Only the nouns change.

---

## Why the Wiki Exists

Without the wiki, answering "why is quality dropping on L4?" means:
- Open maintenance_report_0008.pdf (37 pages)
- Open qc_report_0026.pdf (24 pages)
- Open fmea_worksheet_0050.pdf (18 pages)
- Manually cross-reference machine IDs across all three
- Takes 30–45 minutes

With the wiki:
```sql
CALL ANSWER_QUESTION(
  'L4 has a Cpk of 0.06. What is causing it and which machines are overdue for maintenance?'
);
```
Answer in 15 seconds, with cross-references already embedded.

The wiki is just the pizza story above — pre-compiled, cross-referenced, and searchable.
