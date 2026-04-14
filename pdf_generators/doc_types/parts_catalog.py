"""
parts_catalog.py — Spare Parts Catalog generator.
"""
import io, os, sys, random, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_generator import FACTORY

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white

NAVY    = HexColor("#1B3A6B")
LGREY   = HexColor("#F5F5F5")
ORANGE  = HexColor("#E67E22")
RED     = HexColor("#FFCCCC")
GREEN   = HexColor("#CCFFEE")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(inch, 0.5*inch, f"PARTS CATALOG — {doc.title}")
    canvas.drawRightString(letter[0] - inch, 0.5*inch, f"Page {doc.page}")
    canvas.restoreState()


def _tbl(rows, col_widths, header_rows=1):
    tbl = Table(rows, colWidths=col_widths, repeatRows=header_rows)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,header_rows-1), NAVY),
        ("TEXTCOLOR",(0,0),(-1,header_rows-1), white),
        ("FONTNAME",(0,0),(-1,header_rows-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,header_rows-1), 8),
        ("FONTNAME",(0,header_rows),(-1,-1), "Helvetica"),
        ("FONTSIZE",(0,header_rows),(-1,-1), 7.5),
        ("ROWBACKGROUNDS",(0,header_rows),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 3), ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
        ("ALIGN",(0,0),(-1,-1), "LEFT"), ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    return tbl


def _spend_chart(categories, amounts, seed) -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 3))
    ax1.pie(amounts, labels=[c[:15] for c in categories], autopct='%1.0f%%',
            colors=plt.cm.Blues(np.linspace(0.3, 0.9, len(amounts))), startangle=90)
    ax1.set_title("Spend by Category", fontsize=8, fontweight="bold")
    ax2.barh([c[:18] for c in categories], amounts, color="#1B3A6B", edgecolor="white")
    ax2.set_xlabel("Annual Spend ($k)", fontsize=8)
    ax2.set_title("Annual Parts Spend", fontsize=8, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate(output_path: str, seed: int, max_pages: int = 20) -> None:
    rng = random.Random(seed)
    machines = FACTORY.random_machines(5, seed)
    suppliers = list(FACTORY.suppliers.values())[:5]

    categories = ["Bearings", "Seals & O-Rings", "Belts & Chains", "Electrical",
                  "Hydraulics", "Pneumatics", "Tooling", "Structural"]
    spend = [rng.randint(20, 200) for _ in categories]

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.9*inch, bottomMargin=0.75*inch,
        title=f"PC-{machines[0].machine_id}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2*inch))
    for txt, sz, col in [
        ("SPARE PARTS CATALOG", 22, NAVY),
        (f"Production Equipment — {machines[0].manufacturer}", 13, HexColor("#444444")),
        (f"Issue: {datetime.date.today().year}-{rng.randint(1,4):02d}", 16, ORANGE),
    ]:
        story.append(Paragraph(txt, ParagraphStyle("cv", fontSize=sz, textColor=col,
                                                    fontName="Helvetica-Bold", alignment=1, spaceAfter=10)))
    story.append(Spacer(1, 0.3*inch))
    cov_data = [
        ["Catalog Number:", f"PC-{rng.randint(10000,99999)}"],
        ["Covers Machines:", ", ".join(m.machine_id for m in machines[:3])],
        ["Manufacturer:", machines[0].manufacturer],
        ["Primary Supplier:", suppliers[0].name if suppliers else "OEM"],
        ["Issue Date:", datetime.date.today().isoformat()],
        ["Price List Effective:", (datetime.date.today() - datetime.timedelta(days=rng.randint(0,90))).isoformat()],
        ["Revision:", f"Rev {rng.randint(1,10)}.{rng.randint(0,9)}"],
    ]
    cov_tbl = Table(cov_data, colWidths=[2*inch, 4*inch])
    cov_tbl.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("GRID",(0,0),(-1,-1), 0.4, HexColor("#CCCCCC")),
        ("BACKGROUND",(0,0),(0,-1), LGREY),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(Table([[cov_tbl]], colWidths=[7*inch]))
    story.append(PageBreak())

    # ── Spend Analysis ─────────────────────────────────────────────────────────
    story.append(Paragraph("1. Spend Analysis", h1))
    chart_buf = _spend_chart(categories, spend, seed)
    story.append(Image(chart_buf, width=6.5*inch, height=2.8*inch))
    story.append(Spacer(1, 0.2*inch))
    spend_rows = [["Category", "Annual Spend ($k)", "# Part Numbers", "# Transactions", "Primary Supplier"]]
    for cat, sp in zip(categories, spend):
        spend_rows.append([cat, f"${sp}k", str(rng.randint(10,80)),
                            str(rng.randint(20,200)),
                            suppliers[rng.randint(0,len(suppliers)-1)].name[:25] if suppliers else "OEM"])
    story.append(_tbl(spend_rows, [1.4*inch, 1.3*inch, 1.1*inch, 1.1*inch, 2.1*inch]))
    story.append(PageBreak())

    # ── Master Parts List ──────────────────────────────────────────────────────
    story.append(Paragraph("2. Master Parts List", h1))
    part_descriptions = {
        "Bearings": ["Deep groove ball bearing", "Angular contact bearing", "Tapered roller bearing",
                     "Cylindrical roller bearing", "Thrust bearing", "Needle bearing"],
        "Seals & O-Rings": ["Lip seal", "O-ring NBR 70 Shore", "V-ring seal", "Mechanical face seal",
                             "Shaft seal PTFE", "Piston seal"],
        "Belts & Chains": ["V-belt A-section", "Timing belt HTD 8M", "Roller chain #40",
                            "V-ribbed belt PK", "Flat belt", "Drive chain simplex"],
        "Electrical": ["Contactor 40A 3-pole", "Relay 24VDC", "Fuse 10A fast blow",
                       "Proximity sensor NPN", "Encoder 1024 ppr", "Servo cable 10m"],
        "Hydraulics": ["Hydraulic cylinder", "Pressure relief valve", "Hydraulic pump",
                       "Directional control valve", "Filter element 10μm", "Hydraulic hose 1/4\""],
        "Pneumatics": ["Pneumatic cylinder", "Solenoid valve 5/2", "Air filter element",
                       "Pressure regulator", "Air cylinder seal kit", "FRL unit"],
        "Tooling": ["Carbide insert CNMG 120408", "HSS end mill 10mm", "Drill bit cobalt 8mm",
                    "Boring bar 20mm", "Tap M10×1.5", "Reamer 12H7"],
        "Structural": ["Levelling pad M16", "Way cover bellow", "Chip conveyor hinge",
                       "Cable track 50mm", "Cable drag chain", "Machine mounting bolt M20"],
    }
    n_parts = min(max_pages * 12, 250) if max_pages else 250
    parts_rows = [["Part No.", "OEM Part No.", "Description", "Category", "UOM", "List Price", "Supplier", "Stock", "Lead (days)"]]
    for i in range(n_parts):
        cat = categories[i % len(categories)]
        descs = part_descriptions[cat]
        desc = descs[i % len(descs)]
        m = machines[i % len(machines)]
        sup = suppliers[i % len(suppliers)] if suppliers else None
        stock = rng.choice(["IN STOCK", "IN STOCK", "IN STOCK", "LOW STOCK", "ON ORDER", "SOURCED"])
        parts_rows.append([
            FACTORY.part_number(seed + i, "PC"),
            FACTORY.part_number(seed + i + 1000, "OEM"),
            f"{m.manufacturer[:8]} {desc}"[:30],
            cat[:12],
            rng.choice(["EA", "SET", "PAIR", "M", "PKG"]),
            f"${rng.randint(10, 5000):,}",
            sup.name[:18] if sup else "OEM",
            stock,
            str(rng.randint(1, 60)),
        ])
    pts_tbl = Table(parts_rows,
                    colWidths=[0.9*inch,0.9*inch,1.8*inch,0.9*inch,
                               0.45*inch,0.75*inch,1.1*inch,0.75*inch,0.5*inch],
                    repeatRows=1)
    pts_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 6.5),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 3),
    ]))
    for i, row in enumerate(parts_rows[1:], 1):
        if row[7] == "LOW STOCK":
            pts_tbl.setStyle(TableStyle([("BACKGROUND",(7,i),(7,i), RED)]))
        elif row[7] == "IN STOCK":
            pts_tbl.setStyle(TableStyle([("BACKGROUND",(7,i),(7,i), GREEN)]))
    story.append(pts_tbl)
    story.append(PageBreak())

    # ── Supplier Directory ─────────────────────────────────────────────────────
    story.append(Paragraph("3. Approved Supplier Directory", h1))
    sup_rows = [["Supplier Code", "Name", "Contact", "Phone", "Email", "Lead Time", "Payment Terms", "Rating"]]
    for sup in suppliers:
        sup_rows.append([
            sup.supplier_id,
            sup.name[:22],
            f"{sup.contact[:20]}",
            f"+1-{rng.randint(200,999)}-{rng.randint(100,999)}-{rng.randint(1000,9999)}",
            f"orders@{sup.name[:6].lower().replace(' ','')}.com",
            f"{sup.lead_time_days} days",
            rng.choice(["Net 30", "Net 45", "Net 60", "2/10 Net 30"]),
            f"{round(rng.uniform(3.2,5.0),1)}/5.0",
        ])
    story.append(_tbl(sup_rows, [0.75*inch,1.5*inch,1.1*inch,1.1*inch,1.3*inch,0.75*inch,0.85*inch,0.65*inch]))
    story.append(Spacer(1, 0.3*inch))

    # ── Compatibility Matrix ───────────────────────────────────────────────────
    story.append(Paragraph("4. Machine–Part Compatibility Matrix", h1))
    story.append(Paragraph(
        "The following matrix shows which critical assemblies are compatible with each machine model. "
        "✓ = compatible, ✗ = not compatible, O = optional / requires adapter kit.",
        ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)))
    story.append(Spacer(1, 0.1*inch))
    sub_categories = ["Spindle assy", "Ball screw", "Linear guide", "Servo drive", "Tool changer",
                       "Coolant pump", "Chip conveyor", "Control unit"]
    compat_rows = [["Assembly"] + [m.machine_id for m in machines[:5]]]
    for sub in sub_categories:
        row = [sub]
        for m in machines[:5]:
            row.append(rng.choice(["✓", "✓", "✓", "✗", "O"]))
        compat_rows.append(row)
    compat_tbl = Table(compat_rows, colWidths=[1.5*inch] + [1.1*inch]*5)
    compat_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 9),
        ("FONTNAME",(0,0),(0,-1), "Helvetica-Bold"), ("FONTSIZE",(0,0),(0,-1), 8),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.5, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("ALIGN",(1,0),(-1,-1), "CENTER"),
    ]))
    for i, row in enumerate(compat_rows[1:], 1):
        for j, val in enumerate(row[1:], 1):
            if val == "✓":
                compat_tbl.setStyle(TableStyle([("BACKGROUND",(j,i),(j,i), GREEN)]))
            elif val == "✗":
                compat_tbl.setStyle(TableStyle([("BACKGROUND",(j,i),(j,i), RED)]))
    story.append(compat_tbl)

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
