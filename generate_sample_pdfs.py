"""Generate sample manufacturing PDFs for upload testing.

Usage:
    python3 generate_sample_pdfs.py

Requires: reportlab  (pip install reportlab)

Generates 4 PDFs in the current directory:
  - equipment_spec_hydraulic_press_m200.pdf
  - maintenance_report_m200_2026_q1.pdf
  - sds_hydraulic_fluid_hf5.pdf
  - parts_catalog_0060.pdf
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

STYLES = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=STYLES["Heading1"], fontSize=16, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=STYLES["Heading2"], fontSize=13, spaceAfter=6)
BODY = STYLES["BodyText"]
BODY.spaceAfter = 6


def _spacer():
    return Spacer(1, 0.15 * inch)


def _table(data, col_widths=None):
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A6B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


# ── 1. Equipment Spec: Hydraulic Press M200 ──────────────────────────────────
def gen_equipment_spec():
    doc = SimpleDocTemplate(
        "equipment_spec_hydraulic_press_m200.pdf",
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    story = [
        Paragraph("Equipment Specification — Hydraulic Press M200", H1),
        Paragraph("Document ID: EQSP-M200-2026 | Rev: 2 | Date: 2026-03-15", BODY),
        _spacer(),
        Paragraph("1. Overview", H2),
        Paragraph(
            "The M200 Hydraulic Press is a 200-tonne servo-hydraulic stamping press "
            "installed on Production Line L10. It is used for forming automotive "
            "structural brackets and door reinforcement panels.",
            BODY,
        ),
        _spacer(),
        Paragraph("2. Technical Specifications", H2),
        _table(
            [
                ["Parameter", "Value", "Unit"],
                ["Machine ID", "M200", "—"],
                ["Press Force", "200", "tonne"],
                ["Stroke Length", "600", "mm"],
                ["Slide Speed (working)", "8–25", "mm/s"],
                ["Slide Speed (rapid)", "120", "mm/s"],
                ["Daylight Opening", "1,200", "mm"],
                ["Bed Size (W × D)", "2,400 × 1,800", "mm"],
                ["Motor Power", "75", "kW"],
                ["Operating Pressure", "280", "bar"],
                ["Control System", "Siemens S7-1500 PLC", "—"],
                ["Weight", "42,000", "kg"],
            ],
            col_widths=[2.2 * inch, 2.2 * inch, 1.4 * inch],
        ),
        _spacer(),
        Paragraph("3. Operating Parameters", H2),
        _table(
            [
                ["Parameter", "Min", "Max", "Unit"],
                ["Hydraulic Oil Temperature", "20", "55", "°C"],
                ["Ambient Temperature", "5", "40", "°C"],
                ["Supply Voltage", "380", "415", "V AC 3-phase"],
                ["Air Pressure (pneumatic)", "5.5", "7.0", "bar"],
                ["Cycle Rate (max)", "—", "18", "strokes/min"],
            ],
            col_widths=[2.4 * inch, 1.0 * inch, 1.0 * inch, 1.4 * inch],
        ),
        _spacer(),
        Paragraph("4. Safety Systems", H2),
        Paragraph(
            "• Dual-channel light curtain (IEC 61496-1 Cat. 4 / PLe)\n"
            "• Emergency stop mushroom buttons at all four corners\n"
            "• Hydraulic pressure relief valve: set at 310 bar\n"
            "• Anti-tie-down two-hand control\n"
            "• Perimeter safety fence with interlocked gate",
            BODY,
        ),
        _spacer(),
        Paragraph("5. Maintenance Intervals", H2),
        _table(
            [
                ["Task", "Interval", "Estimated Duration"],
                ["Hydraulic oil level check", "Daily", "5 min"],
                ["Filter element replacement", "Every 500 h", "45 min"],
                ["Full hydraulic oil change", "Every 4,000 h", "4 h"],
                ["Seal kit replacement (cylinder)", "Every 10,000 h", "8 h"],
                ["Annual safety system test", "12 months", "2 h"],
            ],
            col_widths=[2.8 * inch, 1.4 * inch, 1.6 * inch],
        ),
        _spacer(),
        Paragraph("6. Supplier Information", H2),
        Paragraph(
            "Manufacturer: Schuler AG, Göppingen, Germany\n"
            "Local Service Agent: PressServ Australia, Melbourne VIC\n"
            "Service Contact: +61 3 9XXX XXXX | service@pressserv.com.au\n"
            "Spare Parts Lead Time: 4–6 weeks (standard), 48 h (express stock items)",
            BODY,
        ),
    ]
    doc.build(story)
    print("Generated: equipment_spec_hydraulic_press_m200.pdf")


# ── 2. Maintenance Report: M200 Q1 2026 ──────────────────────────────────────
def gen_maintenance_report():
    doc = SimpleDocTemplate(
        "maintenance_report_m200_2026_q1.pdf",
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    story = [
        Paragraph("Maintenance Report — M200 Hydraulic Press | Q1 2026", H1),
        Paragraph("Period: 2026-01-01 to 2026-03-31 | Technician: R. Halloran", BODY),
        _spacer(),
        Paragraph("1. Summary", H2),
        Paragraph(
            "Three scheduled maintenance events and one corrective maintenance event were "
            "completed during Q1 2026. Total downtime attributed to maintenance: 11.5 hours. "
            "The press operated for 1,840 hours during the quarter. No safety incidents were recorded.",
            BODY,
        ),
        _spacer(),
        Paragraph("2. Scheduled Maintenance Log", H2),
        _table(
            [
                ["Date", "Task", "Parts Replaced", "Duration (h)", "Technician"],
                ["2026-01-08", "500 h filter change", "Filter element HF-M200-01", "0.75", "R. Halloran"],
                ["2026-02-12", "500 h filter change", "Filter element HF-M200-01", "0.75", "R. Halloran"],
                ["2026-03-19", "500 h filter change + seal inspection", "Filter element HF-M200-01, O-ring kit OK-M200-03", "2.0", "R. Halloran"],
                ["2026-01-15", "Annual safety system test", "None", "2.0", "R. Halloran + Safety Officer"],
            ],
            col_widths=[1.0 * inch, 1.8 * inch, 1.9 * inch, 0.9 * inch, 1.2 * inch],
        ),
        _spacer(),
        Paragraph("3. Corrective Maintenance", H2),
        Paragraph(
            "Date: 2026-02-27 | Duration: 6.0 hours | Priority: HIGH",
            BODY,
        ),
        Paragraph(
            "Fault: Hydraulic cylinder rod seal leak detected during operator daily check. "
            "Oil seeping from rod end of main cylinder. Press taken offline immediately per "
            "procedure MP-002.",
            BODY,
        ),
        Paragraph(
            "Action: Cylinder rod seals replaced (Part: SK-M200-CYL-A, Qty: 1 kit). "
            "System pressure tested to 310 bar. No further leaks detected. "
            "ALERT: Rod chrome surface showed minor scoring — monitor at next 500 h service. "
            "If scoring progresses, cylinder rod replacement (Part: ROD-M200-A) to be scheduled.",
            BODY,
        ),
        _spacer(),
        Paragraph("4. Hydraulic Oil Analysis", H2),
        _table(
            [
                ["Parameter", "Jan Result", "Mar Result", "Limit", "Status"],
                ["Viscosity @ 40°C (cSt)", "46.2", "46.8", "41–51", "OK"],
                ["Water content (ppm)", "180", "230", "< 500", "OK"],
                ["Particle count ISO 4406", "16/14/11", "17/15/12", "≤ 18/16/13", "OK"],
                ["Acid number (mgKOH/g)", "0.31", "0.44", "< 1.0", "OK"],
                ["Metal particles (Fe ppm)", "12", "28", "< 50", "MONITOR"],
            ],
            col_widths=[2.1 * inch, 0.95 * inch, 0.95 * inch, 1.0 * inch, 0.85 * inch],
        ),
        Paragraph(
            "ALERT: Iron particle count (Fe) trending upward — likely related to cylinder rod "
            "scoring event. Re-sample at 2026-04-15. If Fe > 40 ppm, escalate to Engineering.",
            BODY,
        ),
        _spacer(),
        Paragraph("5. Next Scheduled Maintenance", H2),
        _table(
            [
                ["Planned Date", "Task", "Estimated Duration"],
                ["2026-04-16", "500 h filter change + Fe oil re-sample", "1.5 h"],
                ["2026-06-01", "500 h filter change", "0.75 h"],
                ["2026-07-15", "4,000 h full oil change (due at 4,200 h)", "4 h"],
            ],
            col_widths=[1.4 * inch, 3.2 * inch, 1.4 * inch],
        ),
    ]
    doc.build(story)
    print("Generated: maintenance_report_m200_2026_q1.pdf")


# ── 3. SDS: Hydraulic Fluid HF-5 ─────────────────────────────────────────────
def gen_sds():
    doc = SimpleDocTemplate(
        "sds_hydraulic_fluid_hf5.pdf",
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    story = [
        Paragraph("Safety Data Sheet — Hydraulic Fluid Grade HF-5", H1),
        Paragraph(
            "SDS Number: SDS-HF5-2025 | Revision: 3 | Date: 2025-11-01\n"
            "Supplier: LubriTech Pty Ltd | GHS Compliant (GHS Rev 9)",
            BODY,
        ),
        _spacer(),
        Paragraph("Section 1 — Identification", H2),
        Paragraph(
            "Product Name: LubriTech HF-5 Hydraulic & Circulating Oil\n"
            "Product Code: LT-HF5-20L / LT-HF5-205L\n"
            "Intended Use: Hydraulic system lubricant for industrial presses and machine tools\n"
            "Supplier Emergency: 1800 XXX XXX (24 h)",
            BODY,
        ),
        _spacer(),
        Paragraph("Section 2 — Hazard Identification", H2),
        _table(
            [
                ["GHS Classification", "Signal Word", "Hazard Statement"],
                ["Aspiration hazard Cat 1", "DANGER", "H304 — Fatal if swallowed and enters airways"],
                ["Skin irritant Cat 3", "WARNING", "H316 — Causes mild skin irritation"],
                ["Aquatic Chronic Cat 3", "WARNING", "H412 — Harmful to aquatic life with lasting effects"],
            ],
            col_widths=[2.2 * inch, 1.2 * inch, 2.9 * inch],
        ),
        _spacer(),
        Paragraph("Section 4 — First Aid", H2),
        Paragraph(
            "INHALATION: Remove to fresh air. If breathing difficulty persists, seek medical attention.\n"
            "SKIN: Wash with soap and water for 15 minutes. Remove contaminated clothing.\n"
            "EYES: Flush with copious water for 15 minutes. Seek medical attention.\n"
            "INGESTION: Do NOT induce vomiting. Seek immediate medical attention — aspiration hazard.",
            BODY,
        ),
        _spacer(),
        Paragraph("Section 7 — Handling and Storage", H2),
        Paragraph(
            "Storage Temperature: 5–40 °C\n"
            "Storage Location: Cool, dry, well-ventilated area away from heat sources and ignition.\n"
            "Container: Keep tightly sealed when not in use.\n"
            "Incompatibles: Strong oxidising agents, acids, halogens.\n"
            "ALERT: Do NOT store near food, beverages, or animal feed.",
            BODY,
        ),
        _spacer(),
        Paragraph("Section 8 — PPE Requirements", H2),
        _table(
            [
                ["PPE Item", "Specification", "When Required"],
                ["Gloves", "Nitrile rubber, min 0.3 mm", "All handling"],
                ["Eye protection", "Safety glasses or goggles", "All handling, filling"],
                ["Protective clothing", "Chemical-resistant apron", "Bulk transfers"],
                ["Respiratory protection", "Not normally required", "Confined space / misting"],
            ],
            col_widths=[1.6 * inch, 2.2 * inch, 2.0 * inch],
        ),
        _spacer(),
        Paragraph("Section 9 — Physical Properties", H2),
        _table(
            [
                ["Property", "Value"],
                ["Appearance", "Clear, pale yellow liquid"],
                ["Odour", "Mild petroleum"],
                ["Flash Point (COC)", "222 °C"],
                ["Kinematic Viscosity @ 40°C", "46 cSt"],
                ["Kinematic Viscosity @ 100°C", "6.8 cSt"],
                ["Density @ 15°C", "875 kg/m³"],
                ["Pour Point", "−24 °C"],
                ["Vapour Pressure @ 20°C", "< 0.01 kPa"],
            ],
            col_widths=[2.5 * inch, 3.3 * inch],
        ),
        _spacer(),
        Paragraph("Section 13 — Disposal", H2),
        Paragraph(
            "Do NOT dispose of used hydraulic oil via stormwater drains or soil. "
            "Collect used oil in labelled containers and arrange licensed waste oil collection. "
            "Contact LubriTech or local council for approved disposal contractors.",
            BODY,
        ),
    ]
    doc.build(story)
    print("Generated: sds_hydraulic_fluid_hf5.pdf")


# ── 4. Parts Catalog: M200 Spare Parts ───────────────────────────────────────
def gen_parts_catalog():
    doc = SimpleDocTemplate(
        "parts_catalog_0060.pdf",
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )
    story = [
        Paragraph("Spare Parts Catalog — Hydraulic Press M200", H1),
        Paragraph(
            "Catalog ID: PC-M200-2026 | Machine: M200 | Revision: 1 | Date: 2026-01-10",
            BODY,
        ),
        _spacer(),
        Paragraph("1. Overview", H2),
        Paragraph(
            "This catalog lists recommended spare parts for the M200 Hydraulic Press "
            "(Schuler AG, serial SM200-2022-0847). Parts are categorised as Critical Stock "
            "(must be held on-site), Recommended Stock (hold 1 unit), and Order-on-Demand.",
            BODY,
        ),
        _spacer(),
        Paragraph("2. Critical Stock Parts (hold on-site at all times)", H2),
        _table(
            [
                ["Part Number", "Description", "Qty", "Unit Price (AUD)", "Lead Time", "Supplier"],
                ["HF-M200-01", "Hydraulic return filter element 10µ", "4", "$145", "3 days", "Parker Hannifin"],
                ["SK-M200-CYL-A", "Main cylinder rod seal kit", "2", "$890", "5 days", "Schuler AG / PressServ"],
                ["OK-M200-03", "O-ring assortment kit (press-specific)", "2", "$220", "3 days", "PressServ AU"],
                ["SOL-M200-01", "Directional control solenoid valve 24V DC", "1", "$1,450", "2 weeks", "Bosch Rexroth"],
                ["PRES-M200-A", "Pressure transducer 0–400 bar, 4–20 mA", "1", "$680", "1 week", "Hydrotechnik"],
            ],
            col_widths=[1.2 * inch, 2.0 * inch, 0.4 * inch, 1.1 * inch, 0.9 * inch, 1.2 * inch],
        ),
        _spacer(),
        Paragraph("3. Recommended Stock Parts (hold 1 unit)", H2),
        _table(
            [
                ["Part Number", "Description", "Unit Price (AUD)", "Lead Time", "Supplier"],
                ["ROD-M200-A", "Main cylinder piston rod (chrome)", "$4,200", "6 weeks", "Schuler AG"],
                ["PUMP-M200-01", "Hydraulic axial piston pump 75 cc/rev", "$6,800", "8 weeks", "Bosch Rexroth"],
                ["COOLER-M200", "Oil-to-water heat exchanger", "$1,950", "4 weeks", "Hydac"],
                ["ACCUM-M200", "Nitrogen bladder accumulator 10L 350 bar", "$2,100", "3 weeks", "Hydac"],
                ["PLC-CPU-S7", "Siemens S7-1500 CPU 1515-2 PN", "$3,600", "2 weeks", "Siemens AU"],
            ],
            col_widths=[1.3 * inch, 2.2 * inch, 1.2 * inch, 1.0 * inch, 1.1 * inch],
        ),
        _spacer(),
        Paragraph("4. Consumables (order as needed)", H2),
        _table(
            [
                ["Part Number", "Description", "Unit", "Unit Price (AUD)"],
                ["OIL-HF5-205L", "LubriTech HF-5 Hydraulic Oil 205 L drum", "drum", "$620"],
                ["GREASE-EP2-400G", "EP2 lithium complex grease 400g cartridge", "ea", "$28"],
                ["WIPER-M200-01", "Cylinder wiper ring (external dust seal)", "ea", "$45"],
                ["GAUGE-63-400", "Glycerine pressure gauge 63mm 0–400 bar", "ea", "$95"],
            ],
            col_widths=[1.5 * inch, 2.7 * inch, 0.7 * inch, 1.4 * inch],
        ),
        _spacer(),
        Paragraph("5. Inventory Status — Current", H2),
        _table(
            [
                ["Part Number", "On Hand", "Min Stock", "Reorder Point", "Status"],
                ["HF-M200-01", "2", "4", "2", "ALERT: Below minimum — reorder now"],
                ["SK-M200-CYL-A", "1", "2", "1", "ALERT: At reorder point"],
                ["OK-M200-03", "2", "2", "1", "OK"],
                ["SOL-M200-01", "1", "1", "0", "OK"],
                ["PRES-M200-A", "0", "1", "0", "ALERT: Out of stock — order immediately"],
                ["ROD-M200-A", "0", "1", "0", "ALERT: Out of stock — long lead time (6 wk)"],
            ],
            col_widths=[1.2 * inch, 0.75 * inch, 0.9 * inch, 1.1 * inch, 2.4 * inch],
        ),
        Paragraph(
            "ALERT: HF-M200-01 filter elements are critically low. Next scheduled filter change "
            "is 2026-04-16. Place order immediately to ensure stock availability.",
            BODY,
        ),
    ]
    doc.build(story)
    print("Generated: parts_catalog_0060.pdf")


if __name__ == "__main__":
    gen_equipment_spec()
    gen_maintenance_report()
    gen_sds()
    gen_parts_catalog()
    print("\nAll 4 PDFs generated. Upload them via the Ingest tab in the Streamlit app.")
