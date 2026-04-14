"""
maintenance_report.py — Preventive Maintenance Report generator.
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

NAVY  = HexColor("#1B3A6B")
LGREY = HexColor("#F5F5F5")
RED   = HexColor("#FFCCCC")
GREEN = HexColor("#CCFFEE")
AMBER = HexColor("#FFF3CD")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(inch, 0.5 * inch, f"MAINTENANCE REPORT — {doc.title}")
    canvas.drawRightString(letter[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _tbl(rows, col_widths, header_rows=1):
    tbl = Table(rows, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, header_rows - 1), white),
        ("FONTNAME",   (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, header_rows - 1), 8),
        ("FONTNAME",   (0, header_rows), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, header_rows), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [white, LGREY]),
        ("GRID",       (0, 0), (-1, -1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN",      (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl


def _downtime_chart(machines, downtimes, seed) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 3))
    colors_bar = ["#1B3A6B" if d < 20 else "#E67E22" if d < 40 else "#C0392B" for d in downtimes]
    bars = ax.bar([m.machine_id for m in machines], downtimes, color=colors_bar, edgecolor="white")
    ax.axhline(y=10, color="green", linestyle="--", linewidth=1, label="10% downtime threshold")
    ax.set_xlabel("Machine ID", fontsize=9)
    ax.set_ylabel("Downtime (hours)", fontsize=9)
    ax.set_title("Q1 2025 — Machine Downtime Analysis", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate(output_path: str, seed: int, max_pages: int = 20) -> None:
    rng = random.Random(seed)
    line_id = rng.choice(list(FACTORY.production_lines.keys()))
    line = FACTORY.production_lines[line_id]
    machines = FACTORY.machines_for_line(line_id)[:min(12, len(FACTORY.machines_for_line(line_id)))]
    if not machines:
        machines = list(FACTORY.machines.values())[:8]
    techs = FACTORY.random_technicians(6, seed)
    start_date, end_date = FACTORY.quarter_date_range(seed)
    quarter = f"Q{rng.randint(1,4)} {start_date.year}"

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.9*inch, bottomMargin=0.75*inch,
        title=f"MR-{line_id}-{quarter.replace(' ','-')}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2*inch))
    for txt, sz, col in [
        ("PREVENTIVE MAINTENANCE REPORT", 20, NAVY),
        (f"Production Line {line_id} — {line.product_type}", 14, HexColor("#444444")),
        (quarter, 18, HexColor("#E67E22")),
    ]:
        story.append(Paragraph(txt, ParagraphStyle("cv", fontSize=sz, textColor=col,
                                                    fontName="Helvetica-Bold", alignment=1, spaceAfter=10)))
    story.append(Spacer(1, 0.3*inch))
    cover_meta = [
        ["Report Number:", f"MR-{line_id}-{rng.randint(10000,99999)}"],
        ["Period:", f"{start_date.isoformat()} to {end_date.isoformat()}"],
        ["Prepared by:", techs[0].name if techs else "N/A"],
        ["Reviewed by:", techs[1].name if len(techs) > 1 else "N/A"],
        ["Line Supervisor:", line.supervisor],
        ["Issue Date:", datetime.date.today().isoformat()],
    ]
    cm_tbl = Table(cover_meta, colWidths=[2*inch, 4*inch])
    cm_tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0),(-1,-1), 9),
        ("GRID", (0,0),(-1,-1), 0.4, HexColor("#CCCCCC")),
        ("BACKGROUND", (0,0),(0,-1), LGREY),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
    ]))
    story.append(Table([[cm_tbl]], colWidths=[7*inch]))
    story.append(PageBreak())

    # ── Executive Summary & KPIs ───────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", h1))
    total_tasks = rng.randint(80, 200)
    completed   = int(total_tasks * rng.uniform(0.70, 0.92))
    deferred    = total_tasks - completed - rng.randint(2, 12)
    overdue     = total_tasks - completed - max(deferred, 0)
    labour_hrs  = rng.randint(200, 600)
    parts_cost  = rng.randint(15000, 80000)

    story.append(Paragraph(
        f"This report covers all preventive maintenance activities for Production Line {line_id} "
        f"during {quarter}. A total of <b>{total_tasks}</b> tasks were scheduled, "
        f"of which <b>{completed}</b> ({100*completed//total_tasks}%) were completed on time.",
        body))
    story.append(Spacer(1, 0.15*inch))

    kpi_rows = [
        ["KPI", "Target", "Actual", "Status"],
        ["Total tasks scheduled", "—", str(total_tasks), "—"],
        ["Tasks completed", f"≥{rng.randint(80,95)}%", f"{completed} ({100*completed//total_tasks}%)",
         "✓ ON TARGET" if completed/total_tasks > 0.85 else "⚠ BELOW TARGET"],
        ["Tasks deferred", f"≤5%", str(deferred), "—"],
        ["Tasks overdue", "0", str(max(overdue,0)), "✗ ACTION REQ" if overdue > 0 else "✓ OK"],
        ["Total labour hours", f"≤{labour_hrs+50}", str(labour_hrs), "✓ OK"],
        ["Total parts cost ($)", f"≤{parts_cost+5000}", f"${parts_cost:,}", "✓ WITHIN BUDGET"],
        ["MTBF (avg, hours)", f"≥{rng.randint(400,800)}", str(rng.randint(350,900)), "—"],
        ["MTTR (avg, hours)", f"≤{rng.randint(4,8)}", str(round(rng.uniform(2,10),1)), "—"],
    ]
    kpi_tbl = _tbl(kpi_rows, [2.5*inch, 1.2*inch, 1.5*inch, 1.8*inch])
    # colour overdue row red if > 0
    if max(overdue, 0) > 0:
        kpi_tbl.setStyle(TableStyle([("BACKGROUND", (0,4),(-1,4), RED)]))
    story.append(kpi_tbl)
    story.append(PageBreak())

    # ── Task Completion Log ────────────────────────────────────────────────────
    story.append(Paragraph("2. Task Completion Log", h1))
    statuses = ["COMPLETED"] * 7 + ["DEFERRED"] * 2 + ["OVERDUE"] * 1
    task_types = [
        "Lubricate guide ways", "Replace coolant filter", "Check spindle oil",
        "Inspect servo cooling", "Verify axis backlash", "Clean chip conveyor",
        "Check belt tension", "Replace air filter", "Inspect hydraulic seals",
        "Calibrate thermal compensation", "Check axis home positions",
        "Inspect tool changer", "Test emergency stop", "Update tool offsets",
    ]
    n_tasks = min(max_pages * 10, 250) if max_pages else 250
    task_rows = [["Task ID", "Machine", "Task Description", "Sched. Date", "Comp. Date", "Technician", "Status", "Cost ($)"]]
    for i in range(n_tasks):
        m = machines[i % len(machines)]
        t = techs[i % len(techs)] if techs else None
        status = statuses[i % len(statuses)]
        sched = start_date + datetime.timedelta(days=rng.randint(0, 85))
        comp  = sched + datetime.timedelta(days=rng.randint(0, 3)) if status == "COMPLETED" else ""
        task_rows.append([
            f"T{rng.randint(100000,999999)}",
            m.machine_id,
            task_types[i % len(task_types)],
            sched.isoformat(),
            comp.isoformat() if comp else "—",
            t.name[:18] if t else "—",
            status,
            str(rng.randint(50, 3000)),
        ])

    task_tbl = Table(task_rows, colWidths=[0.8*inch,0.7*inch,2.0*inch,0.9*inch,0.9*inch,1.2*inch,0.9*inch,0.6*inch],
                     repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND", (0,0),(-1,0), NAVY), ("TEXTCOLOR", (0,0),(-1,0), white),
        ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0),(-1,0), 7),
        ("FONTNAME", (0,1),(-1,-1), "Helvetica"), ("FONTSIZE", (0,1),(-1,-1), 6.5),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [white, LGREY]),
        ("GRID", (0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING", (0,0),(-1,-1), 2), ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING", (0,0),(-1,-1), 4), ("ALIGN", (0,0),(-1,-1), "LEFT"),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
    ])
    for i, row in enumerate(task_rows[1:], 1):
        if row[6] == "OVERDUE":
            ts.add("BACKGROUND", (6,i), (6,i), RED)
        elif row[6] == "DEFERRED":
            ts.add("BACKGROUND", (6,i), (6,i), AMBER)
        elif row[6] == "COMPLETED":
            ts.add("BACKGROUND", (6,i), (6,i), GREEN)
    task_tbl.setStyle(ts)
    story.append(task_tbl)
    story.append(PageBreak())

    # ── Downtime Analysis ──────────────────────────────────────────────────────
    story.append(Paragraph("3. Downtime Analysis", h1))
    downtimes = [rng.randint(5, 60) for _ in machines]
    chart_buf = _downtime_chart(machines, downtimes, seed)
    story.append(Image(chart_buf, width=6.5*inch, height=2.8*inch))
    story.append(Spacer(1, 0.2*inch))

    dt_rows = [["Machine ID", "Type", "Total Downtime (hrs)", "# Events", "Primary Cause", "MTBF (hrs)", "MTTR (hrs)"]]
    for m, dt in zip(machines, downtimes):
        dt_rows.append([
            m.machine_id, m.machine_type[:20],
            str(dt),
            str(rng.randint(1, 8)),
            rng.choice(["Wear", "Failure", "Planned", "Setup", "Tooling"]),
            str(rng.randint(200, 900)),
            str(round(rng.uniform(1.5, 12.0), 1)),
        ])
    story.append(_tbl(dt_rows, [0.8*inch,1.8*inch,1.3*inch,0.7*inch,1.2*inch,0.95*inch,0.95*inch]))
    story.append(PageBreak())

    # ── Parts Replacement Log ──────────────────────────────────────────────────
    story.append(Paragraph("4. Parts Replacement Log", h1))
    part_names = ["Spindle bearing", "Coolant pump seal", "Air filter", "Way cover",
                  "Ball screw nut", "Servo drive fuse", "Coolant hose", "Control relay"]
    n_parts = min(max_pages * 8, 160) if max_pages else 160
    parts_rows = [["Part Number", "Description", "Machine", "Qty", "Unit Cost", "Total", "Supplier"]]
    for i in range(n_parts):
        m = machines[i % len(machines)]
        qty = rng.randint(1, 5)
        unit = rng.randint(20, 2500)
        parts_rows.append([
            FACTORY.part_number(seed + i, "RP"),
            part_names[i % len(part_names)],
            m.machine_id,
            str(qty),
            f"${unit:,}",
            f"${qty*unit:,}",
            FACTORY.suppliers[m.supplier_id].name[:18] if m.supplier_id in FACTORY.suppliers else "OEM",
        ])
    story.append(_tbl(parts_rows, [1.1*inch,1.8*inch,0.75*inch,0.5*inch,0.9*inch,0.85*inch,1.6*inch]))
    story.append(PageBreak())

    # ── Next Quarter Schedule ──────────────────────────────────────────────────
    story.append(Paragraph("5. Upcoming Maintenance Schedule", h1))
    story.append(Paragraph(
        f"The following maintenance activities are planned for the next quarter. "
        f"All tasks should be scheduled at least 2 weeks in advance with the maintenance coordinator.",
        body))
    story.append(Spacer(1, 0.15*inch))

    next_start = end_date + datetime.timedelta(days=1)
    next_rows = [["Task ID", "Machine", "Task", "Priority", "Planned Date", "Assigned To", "Est. Hours"]]
    n_next = min(max_pages * 6, 120) if max_pages else 120
    priorities = ["HIGH", "MEDIUM", "LOW"]
    for i in range(n_next):
        m = machines[i % len(machines)]
        t = techs[i % len(techs)] if techs else None
        next_rows.append([
            f"NXT-{rng.randint(10000,99999)}",
            m.machine_id,
            task_types[i % len(task_types)],
            priorities[i % 3],
            (next_start + datetime.timedelta(days=rng.randint(0, 85))).isoformat(),
            t.name[:18] if t else "TBD",
            str(round(rng.uniform(0.5, 8.0), 1)),
        ])
    nxt_tbl = Table(next_rows, colWidths=[0.85*inch,0.75*inch,2.0*inch,0.75*inch,0.95*inch,1.35*inch,0.85*inch],
                    repeatRows=1)
    ts2 = TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 7),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 4),
    ])
    for i, row in enumerate(next_rows[1:], 1):
        if row[3] == "HIGH":
            ts2.add("BACKGROUND", (3,i), (3,i), RED)
    nxt_tbl.setStyle(ts2)
    story.append(nxt_tbl)

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
