"""
production_log.py — Daily Production Log generator.
Covers one week of 3-shift operations on a production line.
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
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white

NAVY    = HexColor("#1B3A6B")
LGREY   = HexColor("#F5F5F5")
RED     = HexColor("#FFCCCC")
GREEN   = HexColor("#CCFFEE")
AMBER   = HexColor("#FFF3CD")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(0.75*inch, 0.5*inch, f"PRODUCTION LOG — {doc.title}")
    canvas.drawRightString(doc.width + 1.5*inch, 0.5*inch, f"Page {doc.page}")
    canvas.restoreState()


def _tbl(rows, col_widths, header_rows=1):
    tbl = Table(rows, colWidths=col_widths, repeatRows=header_rows)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,header_rows-1), NAVY),
        ("TEXTCOLOR",(0,0),(-1,header_rows-1), white),
        ("FONTNAME",(0,0),(-1,header_rows-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,header_rows-1), 7),
        ("FONTNAME",(0,header_rows),(-1,-1), "Helvetica"),
        ("FONTSIZE",(0,header_rows),(-1,-1), 6.5),
        ("ROWBACKGROUNDS",(0,header_rows),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 4),
        ("ALIGN",(0,0),(-1,-1), "LEFT"),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    return tbl


def _oee_chart(dates, availability, performance, quality, seed) -> io.BytesIO:
    x = np.arange(len(dates))
    width = 0.25
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(x - width, availability, width, label="Availability", color="#1B3A6B")
    ax.bar(x,          performance,  width, label="Performance",  color="#E67E22")
    ax.bar(x + width, quality,       width, label="Quality",      color="#27AE60")
    oee = [a*p*q/10000 for a,p,q in zip(availability, performance, quality)]
    ax.plot(x, oee, 'k--', linewidth=1.5, marker='o', markersize=4, label="OEE")
    ax.axhline(y=85, color="red", linestyle=":", linewidth=1, label="85% target")
    ax.set_ylabel("Percentage (%)", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.set_title("OEE Components — Daily Trend", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=7, loc="lower right")
    ax.set_ylim(0, 110)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def _production_chart(dates, targets, actuals, seed) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.plot(dates, targets, 'r--', linewidth=1.5, label="Target", marker='s', markersize=4)
    ax.plot(dates, actuals, color="#1B3A6B", linewidth=2, label="Actual", marker='o', markersize=4)
    ax.fill_between(range(len(dates)), actuals, targets,
                    where=[a<t for a,t in zip(actuals,targets)], alpha=0.2, color="red")
    ax.set_ylabel("Units", fontsize=8)
    ax.set_xlabel("Date", fontsize=8)
    ax.set_title("Daily Production vs. Target", fontsize=9, fontweight="bold")
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=8)
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
    machines = FACTORY.machines_for_line(line_id)[:8]
    if not machines:
        machines = list(FACTORY.machines.values())[:6]
    techs = FACTORY.random_technicians(12, seed)
    start_date, _ = FACTORY.quarter_date_range(seed)

    # 1 week of data
    week_start = start_date
    n_days = 7
    dates = [(week_start + datetime.timedelta(days=i)) for i in range(n_days)]
    date_strs = [d.strftime("%a %m/%d") for d in dates]

    daily_target = line.target_units_per_hour * 24
    daily_actual = [int(daily_target * rng.uniform(0.80, 1.05)) for _ in range(n_days)]
    availability  = [round(rng.uniform(75, 98), 1) for _ in range(n_days)]
    performance   = [round(rng.uniform(80, 99), 1) for _ in range(n_days)]
    quality       = [round(rng.uniform(97, 99.9), 1) for _ in range(n_days)]
    oee_daily     = [round(a*p*q/10000, 1) for a,p,q in zip(availability,performance,quality)]

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.9*inch, bottomMargin=0.75*inch,
        title=f"PL-{line_id}-{week_start.isoformat()}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*inch))
    for txt, sz, col in [
        ("DAILY PRODUCTION LOG", 20, NAVY),
        (f"Production Line {line_id} — {line.product_type}", 14, HexColor("#444444")),
        (f"Week of {week_start.strftime('%B %d, %Y')}", 16, HexColor("#E67E22")),
    ]:
        story.append(Paragraph(txt, ParagraphStyle("cv", fontSize=sz, textColor=col,
                                                    fontName="Helvetica-Bold", alignment=1, spaceAfter=10)))
    story.append(Spacer(1, 0.3*inch))
    cov_data = [
        ["Production Line:", f"Line {line_id} ({line.product_type})"],
        ["Supervisor:", line.supervisor],
        ["Shift Manager:", techs[0].name if techs else "N/A"],
        ["Week Start:", week_start.isoformat()],
        ["Week End:", (week_start + datetime.timedelta(days=6)).isoformat()],
        ["Total Target (week):", f"{daily_target * n_days:,} units"],
        ["Total Actual (week):", f"{sum(daily_actual):,} units"],
        ["Week Attainment:", f"{100*sum(daily_actual)//(daily_target*n_days)}%"],
        ["Report Generated:", datetime.date.today().isoformat()],
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

    # ── Week Summary & OEE ────────────────────────────────────────────────────
    story.append(Paragraph("1. Week Summary", h1))
    week_sum_rows = [["Date", "Shift", "Target", "Actual", "Attain.", "Avail.%", "Perf.%", "Qual.%", "OEE%", "Downtime (h)"]]
    shifts = ["Day", "Swing", "Night"]
    for i, (d, da, av, pf, qu, oe) in enumerate(zip(date_strs, daily_actual, availability, performance, quality, oee_daily)):
        for shift in shifts:
            shift_actual = int(da * rng.uniform(0.28, 0.38))
            shift_dt     = round(rng.uniform(0, 3), 1)
            week_sum_rows.append([d, shift, str(daily_target//3), str(shift_actual),
                                   f"{100*shift_actual//(daily_target//3)}%",
                                   str(av), str(pf), str(qu), str(oe), str(shift_dt)])
    week_sum_tbl = _tbl(week_sum_rows, [0.8*inch,0.6*inch,0.7*inch,0.7*inch,0.6*inch,
                                         0.65*inch,0.65*inch,0.65*inch,0.65*inch,0.85*inch])
    story.append(week_sum_tbl)
    story.append(PageBreak())

    # ── OEE Chart ─────────────────────────────────────────────────────────────
    story.append(Paragraph("2. OEE Analysis", h1))
    oee_buf = _oee_chart(date_strs, availability, performance, quality, seed)
    story.append(Image(oee_buf, width=6.5*inch, height=2.8*inch))
    story.append(Spacer(1, 0.15*inch))
    avg_oee = sum(oee_daily) / len(oee_daily)
    story.append(Paragraph(
        f"Week average OEE: <b>{avg_oee:.1f}%</b> "
        f"(Target: 85%). "
        f"Availability: {sum(availability)/len(availability):.1f}% | "
        f"Performance: {sum(performance)/len(performance):.1f}% | "
        f"Quality: {sum(quality)/len(quality):.1f}%",
        body))
    story.append(Spacer(1, 0.2*inch))

    # ── Production vs Target chart ────────────────────────────────────────────
    prod_buf = _production_chart(date_strs, [daily_target]*n_days, daily_actual, seed)
    story.append(Image(prod_buf, width=6.5*inch, height=2.3*inch))
    story.append(PageBreak())

    # ── Hourly Production Log ─────────────────────────────────────────────────
    story.append(Paragraph("3. Hourly Production Log", h1))
    hourly_rows = [["Date", "Hour", "Shift", "Machine", "SKU", "Target/hr", "Actual/hr", "Scrap", "Operator", "Notes"]]
    n_hours = min(max_pages * 10, 200) if max_pages else 200
    skus = [f"SKU-{rng.randint(1000,9999)}" for _ in range(5)]
    notes_options = ["", "", "", "Tool change", "Speed adjustment", "Material lot change",
                     "Operator break", "Quality check", "Coolant top-up"]
    hour_count = 0
    for day in dates:
        if hour_count >= n_hours:
            break
        for hour in range(0, 24, 1):
            if hour_count >= n_hours:
                break
            m = machines[hour % len(machines)]
            t = techs[hour % len(techs)] if techs else None
            shift = "Day" if 6 <= hour < 14 else "Swing" if 14 <= hour < 22 else "Night"
            target_hr = daily_target // 24
            actual_hr = int(target_hr * rng.uniform(0.75, 1.05))
            scrap = rng.randint(0, 3)
            hourly_rows.append([
                day.strftime("%m/%d"),
                f"{hour:02d}:00",
                shift,
                m.machine_id,
                skus[hour % len(skus)],
                str(target_hr),
                str(actual_hr),
                str(scrap),
                t.name[:14] if t else "—",
                notes_options[hour % len(notes_options)],
            ])
            hour_count += 1
    hourly_tbl = Table(hourly_rows,
                        colWidths=[0.65*inch,0.6*inch,0.6*inch,0.75*inch,0.8*inch,
                                   0.7*inch,0.7*inch,0.5*inch,1.1*inch,0.6*inch],
                        repeatRows=1)
    hourly_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 6.5),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 1.5), ("BOTTOMPADDING",(0,0),(-1,-1), 1.5),
        ("LEFTPADDING",(0,0),(-1,-1), 3),
    ]))
    story.append(hourly_tbl)
    story.append(PageBreak())

    # ── Downtime Events ────────────────────────────────────────────────────────
    story.append(Paragraph("4. Downtime Events Register", h1))
    downtime_codes = {
        "PM": "Planned Maintenance", "UM": "Unplanned Maintenance",
        "SO": "Setup / Changeover", "MT": "Material Shortage",
        "QH": "Quality Hold", "BK": "Breakdown", "TL": "Trial / Testing",
    }
    n_dt = min(max_pages * 5, 100) if max_pages else 100
    dt_rows = [["Date", "Start", "End", "Duration (h)", "Machine", "Code", "Description", "Technician", "Status"]]
    for i in range(n_dt):
        day = dates[i % n_days]
        start_h = rng.randint(0, 22)
        dur = round(rng.uniform(0.25, 4.0), 2)
        end_h = min(start_h + int(dur), 23)
        code = rng.choice(list(downtime_codes.keys()))
        m = machines[i % len(machines)]
        t = techs[i % len(techs)] if techs else None
        dt_rows.append([
            day.strftime("%m/%d"),
            f"{start_h:02d}:00",
            f"{end_h:02d}:00",
            str(dur),
            m.machine_id,
            code,
            downtime_codes[code][:25],
            t.name[:18] if t else "—",
            rng.choice(["Resolved", "Resolved", "Ongoing", "Escalated"]),
        ])
    story.append(_tbl(dt_rows, [0.6*inch,0.6*inch,0.6*inch,0.75*inch,0.75*inch,
                                  0.5*inch,1.6*inch,1.2*inch,0.9*inch]))
    story.append(PageBreak())

    # ── Shift Summary ─────────────────────────────────────────────────────────
    story.append(Paragraph("5. Shift Handover Notes", h1))
    shift_detail_rows = [["Date", "Shift", "Supervisor", "Machines Running", "Notes / Issues"]]
    for day in dates:
        for shift in shifts:
            running = rng.randint(len(machines)//2, len(machines))
            notes_opt = [
                "Normal operations. No issues.",
                f"Machine {machines[0].machine_id} coolant level low — topped up.",
                f"SKU changeover completed at 10:00. 15 min delay.",
                "Quality hold on 2 pallets — awaiting QC disposition.",
                "All machines running at target cycle time.",
                f"Bearing noise on {machines[-1].machine_id} — scheduled for PM.",
            ]
            shift_detail_rows.append([
                day.strftime("%a %m/%d"),
                shift,
                rng.choice([t.name[:20] for t in techs]) if techs else "—",
                str(running),
                notes_opt[rng.randint(0, len(notes_opt)-1)],
            ])
    story.append(_tbl(shift_detail_rows, [0.85*inch, 0.7*inch, 1.5*inch, 1.1*inch, 2.85*inch]))

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
