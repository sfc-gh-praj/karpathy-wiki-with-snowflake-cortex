"""
qc_report.py — Quality Control Report generator.
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


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(inch, 0.5*inch, f"QC REPORT — {doc.title}")
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
        ("TOPPADDING",(0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
        ("ALIGN",(0,0),(-1,-1), "LEFT"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    return tbl


def _defect_trend_chart(dates, defect_rates, threshold, seed) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.plot(range(len(dates)), defect_rates, color="#1B3A6B", linewidth=1.5, marker="o", markersize=3, label="Defect Rate %")
    ax.axhline(y=threshold, color="red", linestyle="--", linewidth=1, label=f"Threshold {threshold}%")
    ax.fill_between(range(len(dates)), defect_rates, alpha=0.1, color="#1B3A6B")
    ax.set_xlabel("Date", fontsize=8)
    ax.set_ylabel("Defect Rate (%)", fontsize=8)
    ax.set_title("Daily Defect Rate Trend", fontsize=10, fontweight="bold")
    step = max(1, len(dates)//8)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def _spc_chart(measurements, ucl, lcl, cl, seed) -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 3.5), sharex=True)
    n = len(measurements)
    subgroups = np.array(measurements).reshape(-1, 5) if n >= 5 else np.array(measurements).reshape(1, -1)
    xbar = subgroups.mean(axis=1)
    r = subgroups.max(axis=1) - subgroups.min(axis=1)

    ax1.plot(xbar, color="#1B3A6B", linewidth=1.5, marker="o", markersize=3)
    ax1.axhline(y=ucl, color="red", linestyle="--", linewidth=1, label=f"UCL={ucl:.3f}")
    ax1.axhline(y=lcl, color="red", linestyle="--", linewidth=1, label=f"LCL={lcl:.3f}")
    ax1.axhline(y=cl,  color="green", linestyle="-", linewidth=1, label=f"CL={cl:.3f}")
    ax1.set_ylabel("X-bar", fontsize=8)
    ax1.set_title("SPC Control Chart — Critical Dimension", fontsize=9, fontweight="bold")
    ax1.legend(fontsize=7, loc="upper right")

    ax2.plot(r, color="#E67E22", linewidth=1.5, marker="s", markersize=3)
    ax2.axhline(y=r.mean()*2.114, color="red", linestyle="--", linewidth=1, label="UCL_R")
    ax2.axhline(y=r.mean(), color="green", linestyle="-", linewidth=1, label="R-bar")
    ax2.set_ylabel("Range", fontsize=8)
    ax2.set_xlabel("Subgroup", fontsize=8)
    ax2.legend(fontsize=7, loc="upper right")
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
    machines = FACTORY.machines_for_line(line_id)[:10]
    if not machines:
        machines = list(FACTORY.machines.values())[:8]
    threshold = line.defect_threshold_pct

    start_date, end_date = FACTORY.quarter_date_range(seed)
    period_label = f"Q{rng.randint(1,4)} {start_date.year}"
    n_days = (end_date - start_date).days + 1
    dates = [(start_date + datetime.timedelta(days=i)).strftime("%m/%d") for i in range(n_days)]
    defect_rates = [round(rng.gauss(threshold, threshold * 0.3), 2) for _ in range(n_days)]
    defect_rates = [max(0.0, min(d, threshold * 3)) for d in defect_rates]
    avg_defect = sum(defect_rates) / len(defect_rates)

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.9*inch, bottomMargin=0.75*inch,
        title=f"QC-{line_id}-{period_label.replace(' ','-')}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2*inch))
    for txt, sz, col in [
        ("QUALITY CONTROL REPORT", 20, NAVY),
        (f"Production Line {line_id} — {line.product_type}", 13, HexColor("#444444")),
        (period_label, 16, HexColor("#E67E22")),
    ]:
        story.append(Paragraph(txt, ParagraphStyle("cv", fontSize=sz, textColor=col,
                                                    fontName="Helvetica-Bold", alignment=1, spaceAfter=10)))
    story.append(Spacer(1, 0.3*inch))
    cov_data = [
        ["Report ID:", f"QCR-{rng.randint(10000,99999)}"],
        ["Line:", f"Line {line_id} — {line.supervisor}"],
        ["Period:", f"{start_date} to {end_date}"],
        ["Product:", line.product_type],
        ["Defect Threshold:", f"{threshold}%"],
        ["Issue Date:", datetime.date.today().isoformat()],
    ]
    cov_tbl = Table(cov_data, colWidths=[2*inch, 4*inch])
    cov_tbl.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("GRID",(0,0),(-1,-1), 0.4, HexColor("#CCCCCC")),
        ("BACKGROUND",(0,0),(0,-1), LGREY),
        ("TOPPADDING",(0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(Table([[cov_tbl]], colWidths=[7*inch]))
    story.append(PageBreak())

    # ── KPI Summary ────────────────────────────────────────────────────────────
    story.append(Paragraph("1. KPI Summary", h1))
    yield_pct = round(100 - avg_defect, 2)
    dpmo = int(avg_defect / 100 * 1_000_000)
    cpk  = round((threshold - avg_defect) / (3 * max(0.01, avg_defect * 0.3)), 2)
    oee  = round(rng.uniform(65, 92), 1)
    kpi_rows = [
        ["KPI", "Target", "Actual", "Status"],
        ["Defect Rate (%)", f"≤ {threshold}%", f"{avg_defect:.2f}%",
         "✓ OK" if avg_defect <= threshold else "✗ ABOVE TARGET"],
        ["Yield (%)",       f"≥ {100-threshold:.1f}%", f"{yield_pct:.2f}%",
         "✓ OK" if yield_pct >= 100 - threshold else "✗ BELOW TARGET"],
        ["DPMO",            f"≤ {int(threshold/100*1e6):,}", f"{dpmo:,}", "—"],
        ["Cpk",             "≥ 1.33", f"{cpk:.2f}",
         "✓ CAPABLE" if cpk >= 1.33 else "✗ NOT CAPABLE"],
        ["OEE (%)",         "≥ 85%", f"{oee}%",
         "✓ OK" if oee >= 85 else "⚠ BELOW TARGET"],
        ["Units produced",  "—", str(rng.randint(5000, 50000)), "—"],
        ["Units scrapped",  "—", str(rng.randint(50, 2000)), "—"],
    ]
    kpi_tbl = _tbl(kpi_rows, [2.4*inch, 1.3*inch, 1.3*inch, 2.0*inch])
    for i, row in enumerate(kpi_rows[1:], 1):
        if "ABOVE" in row[3] or "BELOW" in row[3] or "NOT CAPABLE" in row[3]:
            kpi_tbl.setStyle(TableStyle([("BACKGROUND",(3,i),(3,i), RED)]))
        elif "OK" in row[3] or "CAPABLE" in row[3]:
            kpi_tbl.setStyle(TableStyle([("BACKGROUND",(3,i),(3,i), GREEN)]))
    story.append(kpi_tbl)
    story.append(PageBreak())

    # ── Trend Chart ────────────────────────────────────────────────────────────
    story.append(Paragraph("2. Defect Rate Trend", h1))
    trend_buf = _defect_trend_chart(dates, defect_rates, threshold, seed)
    story.append(Image(trend_buf, width=6.5*inch, height=2.7*inch))
    story.append(Spacer(1, 0.2*inch))
    peak_date = dates[defect_rates.index(max(defect_rates))]
    story.append(Paragraph(
        f"Average defect rate for {period_label}: <b>{avg_defect:.2f}%</b> "
        f"(target ≤ {threshold}%). Peak was <b>{max(defect_rates):.2f}%</b> on {peak_date}. "
        f"{'Performance was within acceptable limits.' if avg_defect <= threshold else 'Performance exceeded the target — corrective actions are required.'}",
        body))
    story.append(PageBreak())

    # ── SPC Chart ──────────────────────────────────────────────────────────────
    story.append(Paragraph("3. SPC Control Chart", h1))
    n_meas = 100
    nominal = rng.uniform(10.0, 100.0)
    std = nominal * rng.uniform(0.001, 0.005)
    measurements = [rng.gauss(nominal, std) for _ in range(n_meas)]
    ucl = nominal + 3 * std
    lcl = nominal - 3 * std
    spc_buf = _spc_chart(measurements, ucl, lcl, nominal, seed)
    story.append(Image(spc_buf, width=6.5*inch, height=3.2*inch))
    story.append(Spacer(1, 0.15*inch))
    out_of_ctrl = sum(1 for m in measurements if m > ucl or m < lcl)
    story.append(Paragraph(
        f"Nominal dimension: <b>{nominal:.3f} mm</b> | UCL: <b>{ucl:.3f}</b> | LCL: <b>{lcl:.3f}</b> | "
        f"Out-of-control points: <b>{out_of_ctrl}</b>/{n_meas}",
        body))
    story.append(PageBreak())

    # ── Defect Detail Table ────────────────────────────────────────────────────
    story.append(Paragraph("4. Defect Detail Log", h1))
    defect_types = ["Dimensional out-of-spec", "Surface finish", "Burr/flash",
                    "Wrong material", "Assembly error", "Marking error",
                    "Leak (pressure test)", "Visual/cosmetic", "Weight out-of-spec"]
    root_causes  = ["Tool wear", "Setup error", "Raw material", "Operator error",
                    "Machine drift", "Coolant issue", "Program error", "Vibration"]
    n_defects = min(max_pages * 12, 350) if max_pages else 350
    defect_rows = [["Date", "Shift", "Machine", "SKU", "Defect Type", "Count", "Root Cause", "Action"]]
    shifts = ["Day", "Night", "Swing"]
    actions = ["Rework", "Scrap", "Return to supplier", "Adjust tooling", "Re-setup machine", "Under investigation"]
    for i in range(n_defects):
        day_offset = rng.randint(0, n_days - 1)
        m = machines[i % len(machines)]
        defect_rows.append([
            (start_date + datetime.timedelta(days=day_offset)).isoformat(),
            rng.choice(shifts),
            m.machine_id,
            f"SKU-{rng.randint(1000,9999)}",
            defect_types[i % len(defect_types)],
            str(rng.randint(1, 25)),
            root_causes[i % len(root_causes)],
            actions[i % len(actions)],
        ])
    defect_tbl = Table(defect_rows,
                       colWidths=[0.85*inch,0.55*inch,0.7*inch,0.75*inch,1.6*inch,0.5*inch,1.0*inch,1.05*inch],
                       repeatRows=1)
    defect_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 7),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 4),
    ]))
    story.append(defect_tbl)
    story.append(PageBreak())

    # ── Cpk per Machine ────────────────────────────────────────────────────────
    story.append(Paragraph("5. Machine Cpk Summary", h1))
    cpk_rows = [["Machine ID", "Type", "Cpk (Feature 1)", "Cpk (Feature 2)", "Cpk (Feature 3)", "Overall Status"]]
    for m in machines:
        c1 = round(rng.uniform(0.8, 1.8), 2)
        c2 = round(rng.uniform(0.8, 1.8), 2)
        c3 = round(rng.uniform(0.8, 1.8), 2)
        status = "CAPABLE" if min(c1, c2, c3) >= 1.33 else ("MARGINAL" if min(c1, c2, c3) >= 1.0 else "NOT CAPABLE")
        cpk_rows.append([m.machine_id, m.machine_type[:22], str(c1), str(c2), str(c3), status])
    cpk_tbl = _tbl(cpk_rows, [0.9*inch, 2.2*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
    story.append(cpk_tbl)
    story.append(Spacer(1, 0.3*inch))

    # ── Corrective Actions ─────────────────────────────────────────────────────
    story.append(Paragraph("6. Corrective Action Register", h1))
    n_ca = min(max_pages * 4, 60) if max_pages else 60
    ca_rows = [["CA ID", "Defect Category", "Root Cause", "Action", "Owner", "Due Date", "Status"]]
    ca_statuses = ["OPEN", "CLOSED", "IN PROGRESS"]
    for i in range(n_ca):
        m = machines[i % len(machines)]
        due = start_date + datetime.timedelta(days=rng.randint(7, 90))
        ca_rows.append([
            f"CA-{rng.randint(1000,9999)}",
            defect_types[i % len(defect_types)],
            root_causes[i % len(root_causes)],
            actions[i % len(actions)],
            m.machine_id,
            due.isoformat(),
            ca_statuses[i % 3],
        ])
    story.append(_tbl(ca_rows, [0.7*inch,1.55*inch,1.0*inch,1.25*inch,0.7*inch,0.85*inch,0.95*inch]))

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
