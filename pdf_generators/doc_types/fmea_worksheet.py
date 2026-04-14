"""
fmea_worksheet.py — Failure Mode & Effects Analysis (FMEA) worksheet generator.
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
DKRED   = HexColor("#8B0000")
RED_BG  = HexColor("#FFCCCC")
AMBER   = HexColor("#FFF3CD")
GREEN   = HexColor("#CCFFEE")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(0.75*inch, 0.5*inch, f"FMEA — {doc.title}")
    canvas.drawRightString(doc.width + 1.5*inch, 0.5*inch, f"Page {doc.page}")
    canvas.restoreState()


def _rpn_chart(items, rpns, seed) -> io.BytesIO:
    # Pareto of top-15 RPN
    idx = sorted(range(len(rpns)), key=lambda i: rpns[i], reverse=True)[:15]
    top_items = [items[i][:25] for i in idx]
    top_rpns  = [rpns[i] for i in idx]
    cumulative = np.cumsum(top_rpns) / sum(top_rpns) * 100

    fig, ax1 = plt.subplots(figsize=(7, 3.5))
    colors = ["#8B0000" if r > 100 else "#E67E22" if r > 50 else "#27AE60" for r in top_rpns]
    ax1.bar(range(len(top_items)), top_rpns, color=colors, edgecolor="white")
    ax2 = ax1.twinx()
    ax2.plot(range(len(top_items)), cumulative, "k-o", linewidth=1.5, markersize=4)
    ax2.axhline(y=80, color="#1B3A6B", linestyle="--", linewidth=1, label="80%")
    ax2.set_ylabel("Cumulative %", fontsize=8)
    ax2.set_ylim(0, 110)
    ax1.axhline(y=100, color="red", linestyle="--", linewidth=1.2, label="RPN=100 threshold")
    ax1.set_ylabel("RPN", fontsize=8)
    ax1.set_xlabel("Failure Mode", fontsize=8)
    ax1.set_title("Pareto Chart — Risk Priority Numbers (Top 15)", fontsize=9, fontweight="bold")
    ax1.set_xticks(range(len(top_items)))
    ax1.set_xticklabels([f"FM{i+1}" for i in range(len(top_items))], fontsize=7)
    ax1.legend(fontsize=7, loc="upper right")
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def _risk_matrix_chart(severities, occurrences, seed) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(4, 3))
    colors = []
    for s, o in zip(severities, occurrences):
        if s >= 8 or o >= 8:
            colors.append("#C0392B")
        elif s >= 5 or o >= 5:
            colors.append("#E67E22")
        else:
            colors.append("#27AE60")
    ax.scatter(occurrences, severities, c=colors, s=60, alpha=0.7, edgecolors="white")
    ax.set_xlim(0, 11); ax.set_ylim(0, 11)
    ax.set_xlabel("Occurrence (O)", fontsize=8)
    ax.set_ylabel("Severity (S)", fontsize=8)
    ax.set_title("Risk Matrix", fontsize=9, fontweight="bold")
    ax.axhline(y=7, color="red", linestyle="--", linewidth=0.8)
    ax.axvline(x=7, color="red", linestyle="--", linewidth=0.8)
    for x in range(1,11): ax.axvline(x=x, color="gray", linewidth=0.2, alpha=0.5)
    for y in range(1,11): ax.axhline(y=y, color="gray", linewidth=0.2, alpha=0.5)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate(output_path: str, seed: int, max_pages: int = 20) -> None:
    rng = random.Random(seed)
    machine = FACTORY.random_machines(1, seed)[0]
    line = FACTORY.production_lines.get(machine.production_line)
    techs = FACTORY.random_technicians(8, seed)

    doc = SimpleDocTemplate(
        output_path, pagesize=landscape(letter),
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.85*inch, bottomMargin=0.75*inch,
        title=f"FMEA-{machine.machine_id}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=14, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=11, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)

    # Build FMEA data ───────────────────────────────────────────────────────────
    subsystems = [
        "Spindle Assembly", "Axis Drive X", "Axis Drive Y", "Axis Drive Z",
        "Coolant System", "Chip Conveyor", "Tool Changer", "Hydraulic System",
        "Electrical Cabinet", "Control Unit", "Lubrication System", "Pneumatic System",
    ]
    failure_modes_by_sub = {
        "Spindle Assembly": ["Excessive vibration", "Thermal overload", "Bearing failure", "Runout out of spec"],
        "Axis Drive X": ["Positional error", "Servo alarm", "Backlash increase", "Drive overload"],
        "Axis Drive Y": ["Positional error", "Servo alarm", "Backlash increase", "Drive overload"],
        "Axis Drive Z": ["Positional error", "Servo alarm", "Backlash increase", "Gravity drop on power loss"],
        "Coolant System": ["Low coolant level", "Pump failure", "Contaminated coolant", "Coolant leak"],
        "Chip Conveyor": ["Chip jam", "Motor overload", "Chain breakage", "Belt wear"],
        "Tool Changer": ["Mis-index", "Tool drop", "ATC arm collision", "Slow tool change"],
        "Hydraulic System": ["Pressure loss", "Hydraulic leak", "Pump cavitation", "Valve sticking"],
        "Electrical Cabinet": ["Overheating", "Ground fault", "PLC communication error", "Power surge"],
        "Control Unit": ["Software fault", "Memory overflow", "Screen failure", "Network timeout"],
        "Lubrication System": ["No lube detected", "Lube line blockage", "Pump failure", "Empty reservoir"],
        "Pneumatic System": ["Air pressure drop", "Air leak", "Valve failure", "Filter clogged"],
    }
    effects_pool = [
        "Machine shutdown", "Dimensional error in part", "Surface finish degradation",
        "Tool breakage", "Part scrap", "Reduced throughput", "Safety hazard to operator",
        "Coolant contamination", "Machine damage", "Unplanned downtime",
    ]
    causes_pool = [
        "Inadequate lubrication", "Wear beyond tolerance", "Operator error",
        "Environmental contamination", "Power fluctuation", "Setup error",
        "PM overdue", "Design limitation", "Thermal cycling fatigue", "Foreign object",
    ]
    controls_pool = [
        "Visual inspection at shift start", "PM every 250 hours", "Automated alarm",
        "SPC monitoring", "Operator training programme", "Torque verification",
        "Laser measurement check", "Pressure switch interlock", "Temperature sensor",
        "Vibration monitoring", "Daily checklist", "ISO 230-2 verification quarterly",
    ]
    actions_pool = [
        "Replace bearing per PM schedule", "Install temperature alarm",
        "Tighten servo tuning parameters", "Add vibration sensor",
        "Increase PM frequency to 125h", "Upgrade coolant filtration",
        "Add pressure relief valve", "Retrain operators on setup procedure",
        "Install flow sensor on lube line", "Replace worn ball screw",
    ]

    fmea_items = []
    for sub in subsystems:
        modes = failure_modes_by_sub.get(sub, ["Generic failure"])
        for mode in modes:
            S = rng.randint(1, 10)
            O = rng.randint(1, 10)
            D = rng.randint(1, 10)
            RPN = S * O * D
            fmea_items.append({
                "subsystem": sub, "mode": mode,
                "effect": rng.choice(effects_pool),
                "cause": rng.choice(causes_pool),
                "S": S, "O": O, "D": D, "RPN": RPN,
                "current_control": rng.choice(controls_pool),
                "recommended_action": rng.choice(actions_pool),
                "responsible": rng.choice([t.name[:18] for t in techs]) if techs else "TBD",
                "target_date": (datetime.date.today() + datetime.timedelta(days=rng.randint(14, 180))).isoformat(),
                "S_new": max(1, S - rng.randint(0, 3)),
                "O_new": max(1, O - rng.randint(0, 3)),
                "D_new": max(1, D - rng.randint(0, 3)),
            })
    fmea_items.sort(key=lambda x: x["RPN"], reverse=True)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*inch))
    for txt, sz, col in [
        ("FAILURE MODE & EFFECTS ANALYSIS", 20, NAVY),
        ("FMEA — Process / Machine FMEA", 13, HexColor("#444444")),
        (f"{machine.machine_id} — {machine.model}", 16, HexColor("#E67E22")),
    ]:
        story.append(Paragraph(txt, ParagraphStyle("cv", fontSize=sz, textColor=col,
                                                    fontName="Helvetica-Bold", alignment=1, spaceAfter=10)))
    story.append(Spacer(1, 0.3*inch))
    cov_data = [
        ["FMEA Number:", f"FMEA-{rng.randint(10000,99999)}"],
        ["Machine:", f"{machine.machine_id} — {machine.model}"],
        ["Machine Type:", machine.machine_type],
        ["Production Line:", machine.production_line or "N/A"],
        ["FMEA Team Lead:", techs[0].name if techs else "N/A"],
        ["Team Members:", ", ".join(t.name[:15] for t in techs[1:4]) if len(techs) > 1 else "N/A"],
        ["Revision Date:", datetime.date.today().isoformat()],
        ["FMEA Type:", "Machine/Process FMEA (PFMEA)"],
        ["Total Failure Modes:", str(len(fmea_items))],
        ["High-Risk (RPN > 100):", str(sum(1 for f in fmea_items if f["RPN"] > 100))],
    ]
    cov_tbl = Table(cov_data, colWidths=[2.2*inch, 5*inch])
    cov_tbl.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1), 9),
        ("GRID",(0,0),(-1,-1), 0.4, HexColor("#CCCCCC")),
        ("BACKGROUND",(0,0),(0,-1), LGREY),
        ("TOPPADDING",(0,0),(-1,-1), 5), ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(Table([[cov_tbl]], colWidths=[10*inch]))
    story.append(PageBreak())

    # ── Scope ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("1. FMEA Scope and Objectives", h1))
    story.append(Paragraph(
        f"This FMEA documents potential failure modes for machine <b>{machine.machine_id}</b> "
        f"({machine.model}, {machine.machine_type}) installed on Production Line {machine.production_line}. "
        f"The objective is to identify, evaluate, and prioritise failure modes to "
        f"guide preventive maintenance and engineering improvements.", body))
    story.append(Spacer(1, 0.15*inch))

    # Severity rating table
    story.append(Paragraph("Severity (S) Rating Scale", h2))
    s_rows = [["Rating", "Description", "Criterion"],
              ["9–10", "Hazardous", "Failure affects safety or causes non-compliance"],
              ["7–8",  "High",      "Major disruption — loss of primary function"],
              ["5–6",  "Moderate",  "Reduced function — some dissatisfaction"],
              ["3–4",  "Low",       "Minor disruption — slight inconvenience"],
              ["1–2",  "Negligible","No discernible effect"],]
    story.append(_tbl_lscape(s_rows, [0.8*inch, 1.5*inch, 6*inch]))
    story.append(Spacer(1, 0.15*inch))

    story.append(Paragraph("Detection (D) Rating Scale", h2))
    d_rows = [["Rating", "Description", "Criterion"],
              ["9–10", "Undetectable", "No detection method available"],
              ["7–8",  "Very Low",     "Manual visual inspection only"],
              ["5–6",  "Moderate",     "Control chart or periodic inspection"],
              ["3–4",  "High",         "Automated in-process detection"],
              ["1–2",  "Almost Certain","100% automated detection with interlock"],]
    story.append(_tbl_lscape(d_rows, [0.8*inch, 1.5*inch, 6*inch]))
    story.append(PageBreak())

    # ── RPN Charts ─────────────────────────────────────────────────────────────
    story.append(Paragraph("2. RPN Analysis", h1))
    rpns = [f["RPN"] for f in fmea_items]
    mode_labels = [f"{f['subsystem'][:15]}: {f['mode'][:20]}" for f in fmea_items]
    pareto_buf = _rpn_chart(mode_labels, rpns, seed)
    story.append(Image(pareto_buf, width=8*inch, height=3.3*inch))
    story.append(Spacer(1, 0.1*inch))

    severities   = [f["S"] for f in fmea_items]
    occurrences  = [f["O"] for f in fmea_items]
    risk_buf = _risk_matrix_chart(severities, occurrences, seed)
    story.append(Image(risk_buf, width=4.5*inch, height=3.2*inch))
    story.append(Spacer(1, 0.1*inch))
    high_rpn = sum(1 for r in rpns if r > 100)
    story.append(Paragraph(
        f"Total failure modes analysed: <b>{len(rpns)}</b> | "
        f"High-risk (RPN > 100): <b>{high_rpn}</b> | "
        f"Max RPN: <b>{max(rpns)}</b> | "
        f"Average RPN: <b>{sum(rpns)//len(rpns)}</b>",
        body))
    story.append(PageBreak())

    # ── FMEA Table ─────────────────────────────────────────────────────────────
    story.append(Paragraph("3. FMEA Worksheet", h1))
    n_fmea = min(len(fmea_items) + max_pages * 2, len(fmea_items)) if max_pages else len(fmea_items)
    # For more rows, repeat items with variation
    display_items = []
    target_rows = min(max_pages * 7, 200) if max_pages else 100
    for i in range(target_rows):
        display_items.append(fmea_items[i % len(fmea_items)])

    fmea_rows = [["#", "Subsystem", "Failure Mode", "Effect", "Cause",
                  "S", "O", "D", "RPN", "Controls", "Rec. Action", "Owner", "RPN*"]]
    for i, item in enumerate(display_items, 1):
        rpn_new = item["S_new"] * item["O_new"] * item["D_new"]
        fmea_rows.append([
            str(i),
            item["subsystem"][:18],
            item["mode"][:22],
            item["effect"][:22],
            item["cause"][:22],
            str(item["S"]),
            str(item["O"]),
            str(item["D"]),
            str(item["RPN"]),
            item["current_control"][:22],
            item["recommended_action"][:22],
            item["responsible"][:12],
            str(rpn_new),
        ])

    fmea_tbl = Table(fmea_rows,
                     colWidths=[0.3*inch, 1.1*inch, 1.4*inch, 1.3*inch, 1.3*inch,
                                0.3*inch, 0.3*inch, 0.3*inch, 0.45*inch,
                                1.4*inch, 1.4*inch, 0.9*inch, 0.45*inch],
                     repeatRows=1)
    fmea_ts = TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 6.5),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 2),
        ("ALIGN",(5,0),(-1,-1), "CENTER"),
    ])
    for i, row in enumerate(fmea_rows[1:], 1):
        rpn = int(row[8])
        if rpn > 100:
            fmea_ts.add("BACKGROUND", (8,i),(8,i), RED_BG)
        elif rpn > 50:
            fmea_ts.add("BACKGROUND", (8,i),(8,i), AMBER)
        else:
            fmea_ts.add("BACKGROUND", (8,i),(8,i), GREEN)
    fmea_tbl.setStyle(fmea_ts)
    story.append(fmea_tbl)
    story.append(PageBreak())

    # ── Action Register ────────────────────────────────────────────────────────
    story.append(Paragraph("4. Corrective Action Register", h1))
    n_actions = min(max_pages * 5, 100) if max_pages else 100
    act_rows = [["#", "Failure Mode", "Recommended Action", "Owner", "Priority",
                 "Due Date", "Status", "Verified By", "RPN Before", "RPN After"]]
    for i, item in enumerate(display_items[:n_actions], 1):
        rpn_new = item["S_new"] * item["O_new"] * item["D_new"]
        priority = "HIGH" if item["RPN"] > 100 else "MEDIUM" if item["RPN"] > 50 else "LOW"
        act_rows.append([
            str(i),
            f"{item['subsystem'][:12]}: {item['mode'][:15]}",
            item["recommended_action"][:28],
            item["responsible"][:12],
            priority,
            item["target_date"],
            rng.choice(["OPEN", "OPEN", "IN PROGRESS", "CLOSED", "CLOSED"]),
            rng.choice([t.name[:12] for t in techs]) if techs else "—",
            str(item["RPN"]),
            str(rpn_new),
        ])
    act_tbl = Table(act_rows,
                    colWidths=[0.35*inch, 1.8*inch, 1.8*inch, 0.9*inch, 0.65*inch,
                               0.85*inch, 0.85*inch, 0.85*inch, 0.65*inch, 0.65*inch],
                    repeatRows=1)
    act_ts = TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 6.5),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 3),
    ])
    for i, row in enumerate(act_rows[1:], 1):
        if row[4] == "HIGH":
            act_ts.add("BACKGROUND", (4,i),(4,i), RED_BG)
        elif row[4] == "MEDIUM":
            act_ts.add("BACKGROUND", (4,i),(4,i), AMBER)
    act_tbl.setStyle(act_ts)
    story.append(act_tbl)

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)


def _tbl_lscape(rows, col_widths, header_rows=1):
    tbl = Table(rows, colWidths=col_widths, repeatRows=header_rows)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,header_rows-1), NAVY),
        ("TEXTCOLOR",(0,0),(-1,header_rows-1), white),
        ("FONTNAME",(0,0),(-1,header_rows-1), "Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,header_rows-1), 8),
        ("FONTNAME",(0,header_rows),(-1,-1), "Helvetica"),
        ("FONTSIZE",(0,header_rows),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,header_rows),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 4), ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
        ("ALIGN",(0,0),(-1,-1), "LEFT"), ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    return tbl
