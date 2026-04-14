"""
equipment_spec.py — Equipment Specification Sheet generator.
Produces a two-column datasheet-style PDF for one machine.
"""
import io, os, sys, random, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_generator import FACTORY

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib import colors

NAVY   = HexColor("#1B3A6B")
LGREY  = HexColor("#F5F5F5")
ORANGE = HexColor("#E67E22")
RED    = HexColor("#C0392B")
GREEN  = HexColor("#27AE60")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(inch, 0.5 * inch, f"CONFIDENTIAL — {doc.title}")
    canvas.drawRightString(letter[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _tbl_style(col_widths=None, header_rows=1):
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR",   (0, 0), (-1, header_rows - 1), white),
        ("FONTNAME",    (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, header_rows - 1), 9),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, LGREY]),
        ("GRID",        (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ])


def _chart_speed_torque(machine, seed) -> io.BytesIO:
    rng = random.Random(seed)
    rpm = np.linspace(0, machine.rpm_max, 50)
    torque = machine.power_kw * 1000 / (rpm + 1) * rng.uniform(0.8, 1.2)
    power  = (torque * rpm) / (9549 * rng.uniform(0.9, 1.1))

    fig, ax1 = plt.subplots(figsize=(7, 3))
    ax2 = ax1.twinx()
    ax1.plot(rpm, torque, color="#1B3A6B", linewidth=2, label="Torque (Nm)")
    ax2.plot(rpm, power,  color="#E67E22", linewidth=2, linestyle="--", label="Power (kW)")
    ax1.set_xlabel("Spindle Speed (RPM)", fontsize=9)
    ax1.set_ylabel("Torque (Nm)", color="#1B3A6B", fontsize=9)
    ax2.set_ylabel("Power (kW)", color="#E67E22", fontsize=9)
    ax1.set_title(f"Speed-Torque-Power Curve — {machine.model}", fontsize=10, fontweight="bold")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate(output_path: str, seed: int, max_pages: int = 20) -> None:
    rng = random.Random(seed)
    machine = FACTORY.random_machines(1, seed)[0]
    supplier = FACTORY.suppliers.get(machine.supplier_id)
    line = FACTORY.production_lines.get(machine.production_line)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.9 * inch, bottomMargin=0.75 * inch,
        title=f"Equipment Spec — {machine.machine_id}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=16, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=12, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], textColor=NAVY, fontSize=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)
    bold = ParagraphStyle("bold", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold")

    story = []

    # ── Cover page ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("EQUIPMENT SPECIFICATION SHEET", ParagraphStyle(
        "cover_title", fontSize=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=1, spaceAfter=12)))
    story.append(Paragraph(machine.model, ParagraphStyle(
        "cover_sub", fontSize=16, textColor=ORANGE, fontName="Helvetica-Bold", alignment=1, spaceAfter=6)))
    story.append(Paragraph(machine.manufacturer, ParagraphStyle(
        "cover_mfr", fontSize=12, textColor=HexColor("#444444"), alignment=1, spaceAfter=24)))

    # placeholder image box
    cover_table = Table([[
        Paragraph(f"[Machine Diagram — {machine.machine_type}]", ParagraphStyle(
            "img_ph", fontSize=11, textColor=HexColor("#888888"), alignment=1))
    ]], colWidths=[5 * inch], rowHeights=[2.5 * inch])
    cover_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.5, HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 0), (-1, -1), LGREY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(Table([[cover_table]], colWidths=[7 * inch]))
    story.append(Spacer(1, 0.3 * inch))

    meta = [
        ["Machine ID:", machine.machine_id, "Production Line:", machine.production_line],
        ["Type:",       machine.machine_type, "Bay:",           machine.bay],
        ["Manufacturer:", machine.manufacturer, "Supplier:", supplier.name if supplier else "N/A"],
        ["Install Date:", machine.install_date, "Document Rev:", f"Rev {rng.randint(1,5)}.{rng.randint(0,9)}"],
        ["Serial Number:", FACTORY.serial_number(seed), "Document Date:", datetime.date.today().isoformat()],
    ]
    meta_tbl = Table(meta, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 0), (0, -1), LGREY),
        ("BACKGROUND", (2, 0), (2, -1), LGREY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())

    # ── Technical Specifications ────────────────────────────────────────────────
    story.append(Paragraph("1. Technical Specifications", h1))
    story.append(Spacer(1, 0.1 * inch))

    spec_rows = [
        ["Parameter", "Value", "Unit", "Tolerance"],
        ["Machine Type", machine.machine_type, "—", "—"],
        ["Max Spindle Speed", str(machine.rpm_max), "RPM", "±50"],
        ["Number of Axes", str(machine.axes), "axes", "—"],
        ["Positional Tolerance", str(machine.tolerance_mm), "mm", "ISO 230-2"],
        ["Power Rating", str(machine.power_kw), "kW", "±2%"],
        ["Machine Weight", str(machine.weight_kg), "kg", "±1%"],
        ["Coolant Capacity", str(rng.randint(80, 400)), "L", "—"],
        ["Tool Magazine Capacity", str(rng.choice([20, 24, 32, 40, 60])), "tools", "—"],
        ["Rapid Traverse X", str(rng.randint(20, 60)), "m/min", "—"],
        ["Rapid Traverse Y", str(rng.randint(20, 60)), "m/min", "—"],
        ["Rapid Traverse Z", str(rng.randint(15, 50)), "m/min", "—"],
        ["Spindle Taper", rng.choice(["CAT 40", "CAT 50", "BT 40", "HSK 63A"]), "—", "—"],
        ["Cutting Feed Rate", str(rng.randint(1, 30000)), "mm/min", "—"],
        ["Max Workpiece Weight", str(rng.randint(200, 2000)), "kg", "—"],
        ["Table Size (X×Y)", f"{rng.randint(400,1200)}×{rng.randint(400,800)}", "mm", "—"],
        ["Axis Travel X", str(rng.randint(300, 1200)), "mm", "—"],
        ["Axis Travel Y", str(rng.randint(300, 800)), "mm", "—"],
        ["Axis Travel Z", str(rng.randint(300, 700)), "mm", "—"],
        ["Spindle Motor", str(rng.randint(7, 37)), "kW", "—"],
        ["Servo Motor (each axis)", str(rng.randint(1, 15)), "kW", "—"],
        ["Coolant Pressure", str(rng.randint(30, 100)), "bar", "—"],
        ["Air Supply Pressure", str(rng.randint(5, 10)), "bar", "—"],
        ["Noise Level", str(rng.randint(72, 88)), "dB(A)", "ISO 4871"],
        ["Vibration Level", str(round(rng.uniform(0.5, 4.5), 1)), "mm/s²", "ISO 10816"],
    ]
    spec_tbl = Table(spec_rows, colWidths=[2.5*inch, 1.8*inch, 1.1*inch, 1.6*inch])
    spec_tbl.setStyle(_tbl_style())
    story.append(spec_tbl)
    story.append(PageBreak())

    # ── Component Specifications ─────────────────────────────────────────────
    story.append(Paragraph("2. Component Specifications", h1))
    components = [
        ("Spindle Assembly",   [("Type", rng.choice(["Direct Drive","Belt Drive","Gear Drive"])), ("Bearing type", "Angular contact"), ("Max torque", f"{rng.randint(100,800)} Nm"), ("Lubrication", "Oil-air mist"), ("Thermal compensation", "Yes"), ("Encoder resolution", f"{rng.randint(1000,16384)} pulses/rev")]),
        ("Control System",     [("Controller", rng.choice(["FANUC 31i-B","Siemens 840D","Mitsubishi M80","Mazatrol"])), ("Display", "15-inch TFT touch"), ("Memory", f"{rng.randint(128,512)} MB"), ("Part program storage", f"{rng.randint(500,5000)} programs"), ("Remote access", "Ethernet / USB")]),
        ("Coolant System",     [("Type", rng.choice(["Flood","Mist","High-pressure","Through-spindle"])), ("Pump type", "Centrifugal"), ("Tank capacity", f"{rng.randint(80,400)} L"), ("Filtration", "Drum filter + chip conveyor"), ("Nozzle count", str(rng.randint(4,12)))]),
        ("Chip Conveyor",      [("Type", rng.choice(["Hinge belt","Scraper","Magnetic"])), ("Discharge height", f"{rng.randint(600,1200)} mm"), ("Speed", f"{rng.randint(3,15)} m/min"), ("Capacity", f"{rng.randint(50,200)} kg/hr")]),
    ]
    for cname, cparams in components:
        story.append(Paragraph(cname, h2))
        crow = [["Parameter", "Value"]] + [[p, v] for p, v in cparams]
        ctbl = Table(crow, colWidths=[3*inch, 4*inch])
        ctbl.setStyle(_tbl_style())
        story.append(ctbl)
        story.append(Spacer(1, 0.15 * inch))
    story.append(PageBreak())

    # ── Performance Curve ────────────────────────────────────────────────────
    story.append(Paragraph("3. Performance Curves", h1))
    story.append(Spacer(1, 0.1 * inch))
    chart_buf = _chart_speed_torque(machine, seed)
    story.append(Image(chart_buf, width=6.5 * inch, height=2.8 * inch))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(
        f"The above chart shows the speed-torque-power envelope for {machine.model}. "
        f"Maximum continuous power of {machine.power_kw} kW is available across the operating range. "
        f"Peak torque is achieved at low speeds for heavy roughing operations.",
        body))
    story.append(PageBreak())

    # ── Maintenance Schedule ─────────────────────────────────────────────────
    story.append(Paragraph("4. Preventive Maintenance Schedule", h1))
    maint_intervals = ["Daily", "Weekly", "Monthly", "Quarterly", "Semi-Annual", "Annual"]
    maint_tasks = [
        ("Check spindle oil level", "Daily", 5, "Visual inspection"),
        ("Clean chip conveyor filter", "Daily", 10, "Compressed air, brush"),
        ("Check coolant concentration", "Daily", 10, "Refractometer"),
        ("Lubricate guide ways", "Weekly", 20, "Oil can, lube chart"),
        ("Check all axis home positions", "Weekly", 15, "Program O9001"),
        ("Inspect belt drive tension", "Weekly", 20, "Belt tension gauge"),
        ("Replace coolant filter", "Monthly", 30, "Replacement filter, drain pan"),
        ("Clean ball screws and guides", "Monthly", 45, "Clean cloth, way oil"),
        ("Check spindle runout", "Monthly", 30, "Dial indicator, arbor"),
        ("Inspect servo drive cooling fans", "Monthly", 15, "Visual"),
        ("Verify axis backlash", "Quarterly", 60, "Ball bar, software"),
        ("Replace spindle oil", "Quarterly", 90, "Drain, refill kit"),
        ("Check all electrical connections", "Quarterly", 45, "Torque wrench"),
        ("Clean control cabinet filters", "Quarterly", 30, "Vacuum, new filters"),
        ("Inspect hydraulic system pressure", "Quarterly", 30, "Pressure gauge"),
        ("Replace coolant fully", "Semi-Annual", 120, "Drain, clean, refill"),
        ("Spindle vibration analysis", "Semi-Annual", 60, "Vibration analyzer"),
        ("Laser calibration all axes", "Annual", 240, "Laser interferometer"),
        ("Replace drive belts if worn", "Annual", 120, "New belts, tension gauge"),
        ("Full electrical safety inspection", "Annual", 180, "Certified electrician"),
    ]
    rows_per_page = 22
    n_maint = min(len(maint_tasks) * (max_pages // 5), 200) if max_pages else 200
    maint_rows = [["Task", "Interval", "Time (min)", "Tools / Notes"]]
    for i in range(n_maint):
        t = maint_tasks[i % len(maint_tasks)]
        maint_rows.append([t[0], t[1], str(t[2] + rng.randint(-5,5)), t[3]])
    maint_tbl = Table(maint_rows, colWidths=[2.8*inch, 1.1*inch, 1.0*inch, 2.1*inch])
    maint_tbl.setStyle(_tbl_style())
    story.append(maint_tbl)
    story.append(PageBreak())

    # ── Parts List ──────────────────────────────────────────────────────────
    story.append(Paragraph("5. Recommended Spare Parts", h1))
    part_types = ["Spindle bearing", "Ball screw nut", "Linear guide block", "Servo drive",
                  "Coolant pump seal", "Way cover", "Tool holder", "Encoder cable",
                  "Air filter element", "Lubrication pump", "Contactor", "Power supply"]
    n_parts = min(max_pages * 8, 180) if max_pages else 180
    parts_rows = [["Part Number", "Description", "Qty", "Unit", "Supplier", "Lead (days)"]]
    for i in range(n_parts):
        ptype = part_types[i % len(part_types)]
        parts_rows.append([
            FACTORY.part_number(seed + i, "SP"),
            f"{machine.manufacturer} {ptype} — {machine.model}",
            str(rng.randint(1, 5)),
            rng.choice(["EA", "SET", "PAIR", "PKG"]),
            supplier.name if supplier else "OEM",
            str(rng.randint(5, 60)),
        ])
    parts_tbl = Table(parts_rows, colWidths=[1.3*inch, 2.7*inch, 0.5*inch, 0.55*inch, 1.5*inch, 0.9*inch])
    parts_tbl.setStyle(_tbl_style())
    story.append(parts_tbl)
    story.append(PageBreak())

    # ── Installation Requirements ────────────────────────────────────────────
    story.append(Paragraph("6. Installation Requirements", h1))
    install_data = [
        ["Utility", "Requirement", "Notes"],
        ["Power supply", f"{rng.choice(['3-phase 400V','3-phase 480V','3-phase 200V'])} ±10%", "Dedicated circuit required"],
        ["Power consumption", f"{machine.power_kw + rng.randint(2,10)} kVA", "Including all ancillaries"],
        ["Compressed air", f"{rng.randint(5,8)} bar, {rng.randint(100,400)} L/min", "Clean, dry (ISO 8573-1 Class 2)"],
        ["Coolant supply", f"{rng.randint(10,50)} L/min at {rng.randint(3,8)} bar", "Filtered to 50 μm"],
        ["Floor load capacity", f"Min {int(machine.weight_kg * 1.5)} kg/m²", "Reinforced concrete recommended"],
        ["Levelling pads", f"{rng.randint(4,8)} anchor points", "M20 bolts, epoxy grout"],
        ["Clearance — front", f"{rng.randint(1000,2000)} mm", "For pallet/workpiece loading"],
        ["Clearance — rear", f"{rng.randint(600,1200)} mm", "Service access"],
        ["Clearance — sides", f"{rng.randint(600,1000)} mm each", "Chip conveyor access"],
        ["Ambient temperature", f"{rng.randint(15,18)}°C – {rng.randint(25,30)}°C", "Thermal stability critical"],
        ["Humidity", "30% – 75% RH", "Non-condensing"],
        ["Vibration isolation", rng.choice(["Levelling mounts", "Isolation pads", "Inertia base"]), "Isolate from press/forge equipment"],
    ]
    inst_tbl = Table(install_data, colWidths=[1.8*inch, 2.5*inch, 2.7*inch])
    inst_tbl.setStyle(_tbl_style())
    story.append(inst_tbl)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Safety Certifications", h2))
    cert_data = [
        ["Standard", "Scope", "Status"],
        ["CE Marking", "Machinery Directive 2006/42/EC", "Certified"],
        ["ISO 16090-1", "Machine tools safety — Machining centres", "Compliant"],
        ["IEC 60204-1", "Electrical equipment of machines", "Compliant"],
        ["NFPA 79", "Electrical standard for industrial machinery (USA)", "Compliant"],
        ["UL 508A", "Industrial control panels", "Listed"],
    ]
    cert_tbl = Table(cert_data, colWidths=[1.8*inch, 3.5*inch, 1.7*inch])
    cert_tbl.setStyle(_tbl_style())
    story.append(cert_tbl)

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
