"""
safety_data_sheet.py — Safety Data Sheet (SDS/MSDS) generator.
Follows the 16-section GHS/OSHA HazCom 2012 format.
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
RED     = HexColor("#C0392B")
ORANGE  = HexColor("#E67E22")
YELLOW  = HexColor("#F9C74F")
DKRED   = HexColor("#8B0000")


def _page_num(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#666666"))
    canvas.drawString(inch, 0.5*inch, f"SDS — {doc.title} | Revision: {doc.author}")
    canvas.drawRightString(letter[0] - inch, 0.5*inch, f"Page {doc.page}")
    canvas.restoreState()


def _section(title, story, h1):
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(title, h1))
    story.append(Spacer(1, 0.05*inch))


def _kv_table(rows, story):
    tbl = Table(rows, colWidths=[2.5*inch, 4.5*inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0),(-1,-1), 8.5),
        ("GRID", (0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("BACKGROUND", (0,0),(0,-1), LGREY),
        ("TOPPADDING", (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0),(-1,-1), 6),
        ("VALIGN", (0,0),(-1,-1), "TOP"),
    ]))
    story.append(tbl)


def _exposure_chart(components, tlvs, seed) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 2.5))
    colors = ["#1B3A6B" if t >= 50 else "#E67E22" if t >= 10 else "#C0392B" for t in tlvs]
    ax.barh([c[:20] for c in components], tlvs, color=colors, edgecolor="white")
    ax.set_xlabel("TLV-TWA (ppm)", fontsize=8)
    ax.set_title("Occupational Exposure Limits (TLV-TWA)", fontsize=9, fontweight="bold")
    ax.axvline(x=10, color="orange", linestyle="--", linewidth=1, label="10 ppm")
    ax.axvline(x=50, color="green",  linestyle="--", linewidth=1, label="50 ppm")
    ax.legend(fontsize=7)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate(output_path: str, seed: int, max_pages: int = 20) -> None:
    rng = random.Random(seed)
    chem = FACTORY.random_chemicals(1, seed)[0]

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.9*inch, bottomMargin=0.75*inch,
        title=f"SDS — {chem.name}",
        author=f"Rev {rng.randint(1,5)}.{rng.randint(0,9)}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading2"], textColor=white, fontSize=10,
                         fontName="Helvetica-Bold", backColor=NAVY, spaceAfter=4,
                         leftIndent=-6, rightIndent=-6, spaceBefore=6,
                         borderPad=4)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9, leading=13)
    warn = ParagraphStyle("warn", parent=styles["Normal"], fontSize=9, leading=13, textColor=DKRED)

    story = []

    # ── Cover Banner ───────────────────────────────────────────────────────────
    banner = Table([[Paragraph(
        f"SAFETY DATA SHEET<br/>GHS / OSHA HazCom 2012 Compliant",
        ParagraphStyle("banner", fontSize=16, textColor=white, fontName="Helvetica-Bold",
                       alignment=1))]], colWidths=[7*inch], rowHeights=[0.9*inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("VALIGN",(0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.2*inch))

    # GHS hazard diamond
    ghs_classes = ["Flammable", "Toxic", "Corrosive", "Irritant", "Health Hazard", "Environmental"]
    selected = rng.sample(ghs_classes, rng.randint(2,4))
    ghs_line = "  |  ".join([f"[{c}]" for c in selected])
    story.append(Paragraph(f"<b>GHS Hazard Classes:</b> {ghs_line}", ParagraphStyle(
        "ghs", fontSize=10, textColor=DKRED, fontName="Helvetica-Bold", spaceAfter=8)))

    # ── Section 1 — Identification ──────────────────────────────────────────────
    _section("SECTION 1 — IDENTIFICATION", story, h1)
    _kv_table([
        ["Product Name:", chem.name],
        ["Product Code:", chem.cas_number.replace("-","") + f"-{rng.randint(100,999)}"],
        ["CAS Number:", chem.cas_number],
        ["Chemical Family:", chem.chem_type],
        ["Hazard Class:", chem.hazard_class],
        ["Intended Use:", f"Industrial manufacturing — {chem.chem_type}"],
        ["Manufacturer:", rng.choice(["LabChem Inc.", "Sigma-Aldrich", "VWR International", "Thermo Fisher"])],
        ["Emergency Phone:", f"+1-{rng.randint(200,999)}-{rng.randint(100,999)}-{rng.randint(1000,9999)} (24/7)"],
        ["Revision Date:", datetime.date.today().isoformat()],
    ], story)

    # ── Section 2 — Hazard Identification ─────────────────────────────────────
    _section("SECTION 2 — HAZARD IDENTIFICATION", story, h1)
    story.append(Paragraph(f"<b>Signal Word:</b> {'DANGER' if 'Toxic' in selected or 'Flammable' in selected else 'WARNING'}", warn))
    hazard_stmts = [
        "H225 — Highly flammable liquid and vapour",
        "H302 — Harmful if swallowed",
        "H311 — Toxic in contact with skin",
        "H331 — Toxic if inhaled",
        "H411 — Toxic to aquatic life with long lasting effects",
        "H315 — Causes skin irritation",
        "H319 — Causes serious eye irritation",
        "H335 — May cause respiratory irritation",
    ]
    precautions = [
        "P210 — Keep away from heat/sparks/open flames",
        "P260 — Do not breathe dust/fumes/gas/mist/vapours",
        "P271 — Use only outdoors or in a well-ventilated area",
        "P273 — Avoid release to the environment",
        "P280 — Wear protective gloves/protective clothing/eye protection",
        "P301+P330+P331 — IF SWALLOWED: Rinse mouth. Do NOT induce vomiting",
        "P304+P340 — IF INHALED: Remove to fresh air and keep at rest",
    ]
    story.append(Paragraph("<b>Hazard Statements:</b>", body))
    for h in rng.sample(hazard_stmts, min(4, len(hazard_stmts))):
        story.append(Paragraph(f"• {h}", body))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("<b>Precautionary Statements:</b>", body))
    for p in rng.sample(precautions, min(4, len(precautions))):
        story.append(Paragraph(f"• {p}", body))

    # ── Section 3 — Composition ────────────────────────────────────────────────
    _section("SECTION 3 — COMPOSITION / INFORMATION ON INGREDIENTS", story, h1)
    n_comp = rng.randint(2, 5)
    comp_names = [chem.name] + [FACTORY.random_chemicals(1, seed+i)[0].name for i in range(1, n_comp)]
    comp_pcts  = [rng.uniform(10, 80) for _ in comp_names]
    total = sum(comp_pcts); comp_pcts = [round(p/total*100, 1) for p in comp_pcts]
    comp_cas   = [chem.cas_number] + [FACTORY.random_chemicals(1, seed+i+100)[0].cas_number for i in range(n_comp-1)]
    comp_rows  = [["Component", "CAS Number", "Concentration (%)", "EC Number", "Classification"]]
    for name, cas, pct in zip(comp_names, comp_cas, comp_pcts):
        comp_rows.append([name[:30], cas, f"{pct}%",
                          f"{rng.randint(200,900)}-{rng.randint(100,999)}-{rng.randint(0,9)}",
                          rng.choice(["Flam. Liq. 2", "Acute Tox. 4", "Skin Irrit. 2", "Eye Irrit. 2"])])
    comp_tbl = Table(comp_rows, colWidths=[1.9*inch,1.1*inch,1.3*inch,1.2*inch,1.5*inch])
    comp_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
        ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,0), 8),
        ("FONTNAME",(0,1),(-1,-1), "Helvetica"), ("FONTSIZE",(0,1),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, LGREY]),
        ("GRID",(0,0),(-1,-1), 0.3, HexColor("#CCCCCC")),
        ("TOPPADDING",(0,0),(-1,-1), 4), ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",(0,0),(-1,-1), 5),
    ]))
    story.append(comp_tbl)
    story.append(PageBreak())

    # ── Section 4 — First Aid ──────────────────────────────────────────────────
    _section("SECTION 4 — FIRST AID MEASURES", story, h1)
    _kv_table([
        ["Eye contact:", "Immediately flush eyes with large amounts of water for at least 15 minutes. Seek medical attention."],
        ["Skin contact:", "Remove contaminated clothing. Wash thoroughly with soap and water. If irritation persists, seek medical attention."],
        ["Inhalation:", "Move to fresh air immediately. If not breathing, give artificial respiration. Seek medical attention."],
        ["Ingestion:", "Do NOT induce vomiting. Rinse mouth. Seek immediate medical attention. Show this SDS to physician."],
        ["Notes to physician:", f"Treat symptomatically. Specific antidote: {rng.choice(['None known','Activated charcoal','N-acetylcysteine','Atropine']).lower()}."],
    ], story)

    # ── Section 5 — Firefighting ───────────────────────────────────────────────
    _section("SECTION 5 — FIREFIGHTING MEASURES", story, h1)
    flash_pt = rng.randint(-20, 100)
    _kv_table([
        ["Flash Point:", f"{flash_pt}°C ({flash_pt*9//5+32}°F) — {'EXTREMELY FLAMMABLE' if flash_pt < 0 else 'FLAMMABLE' if flash_pt < 38 else 'COMBUSTIBLE'}"],
        ["Auto-ignition Temp:", f"{rng.randint(200, 500)}°C"],
        ["Explosive Limits:", f"LEL: {round(rng.uniform(1,4),1)}%  |  UEL: {round(rng.uniform(8,20),1)}%"],
        ["Extinguishing Media:", rng.choice(["CO₂, dry chemical, foam, water spray", "Alcohol-resistant foam, CO₂, dry powder", "Water fog, CO₂, dry chemical"])],
        ["Special Hazards:", "May produce toxic gases on combustion. Vapours may form explosive mixtures with air."],
        ["PPE for Firefighters:", "Full protective gear, self-contained breathing apparatus (SCBA)."],
    ], story)

    # ── Section 6 — Accidental Release ────────────────────────────────────────
    _section("SECTION 6 — ACCIDENTAL RELEASE MEASURES", story, h1)
    story.append(Paragraph(
        "Evacuate non-essential personnel. Eliminate all sources of ignition. "
        "Wear full PPE as described in Section 8. Absorb spill with inert material (vermiculite, dry sand). "
        "Collect in appropriate sealed container for disposal. Prevent entry into sewers and waterways. "
        "Notify relevant regulatory authorities if a reportable quantity is released.", body))
    story.append(PageBreak())

    # ── Section 7 — Handling & Storage ───────────────────────────────────────
    _section("SECTION 7 — HANDLING AND STORAGE", story, h1)
    _kv_table([
        ["Handling precautions:", "Use in well-ventilated areas. Avoid contact with eyes, skin and clothing. "
                                    "Keep away from heat and open flames. Ground containers when transferring."],
        ["Storage conditions:", f"Store at {rng.randint(5,25)}–{rng.randint(26,40)}°C in tightly sealed containers. "
                                  "Keep away from oxidisers, strong acids and bases."],
        ["Incompatibilities:", rng.choice(["Strong oxidising agents, strong acids", "Alkali metals, peroxides",
                                            "Bases, strong reducing agents", "Acids, water"])],
        ["Special packaging:", "Use original container. Do not store with food or beverages."],
    ], story)

    # ── Section 8 — Exposure Controls / PPE ───────────────────────────────────
    _section("SECTION 8 — EXPOSURE CONTROLS / PERSONAL PROTECTION", story, h1)
    tlvs = [rng.randint(1, 200) for _ in comp_names]
    exp_chart = _exposure_chart(comp_names, tlvs, seed)
    story.append(Image(exp_chart, width=5.5*inch, height=2.3*inch))
    story.append(Spacer(1, 0.1*inch))
    _kv_table([
        ["OSHA PEL (TWA):", f"{rng.randint(1,500)} ppm / {rng.randint(1,500)} mg/m³"],
        ["ACGIH TLV-TWA:", f"{rng.randint(1,200)} ppm"],
        ["ACGIH TLV-STEL:", f"{rng.randint(50,500)} ppm — Short-term exposure limit"],
        ["Engineering controls:", "Local exhaust ventilation, enclosed processes. General dilution ventilation."],
        ["Respiratory protection:", rng.choice(["NIOSH N95", "Half-face respirator with OV cartridge",
                                                 "Full-face respirator with ABEK cartridge", "SCBA"])],
        ["Hand protection:", rng.choice(["Nitrile gloves 0.1 mm", "Butyl rubber gloves", "Neoprene gloves ≥0.3 mm"])],
        ["Eye protection:", "Safety goggles (indirect vent) or face shield."],
        ["Body protection:", "Chemical-resistant apron, lab coat. Antistatic clothing if flammable."],
    ], story)
    story.append(PageBreak())

    # ── Sections 9-12 ─────────────────────────────────────────────────────────
    _section("SECTION 9 — PHYSICAL AND CHEMICAL PROPERTIES", story, h1)
    _kv_table([
        ["Appearance:", rng.choice(["Colourless liquid", "Pale yellow liquid", "White powder", "Clear viscous liquid", "Blue-green liquid"])],
        ["Odour:", rng.choice(["Characteristic", "Mild aromatic", "Pungent", "Odourless", "Sweet"])],
        ["Odour threshold:", f"{round(rng.uniform(0.1, 50),1)} ppm"],
        ["pH:", f"{round(rng.uniform(2,12),1)} (1% solution, 20°C)"],
        ["Melting point:", f"{rng.randint(-80,20)}°C"],
        ["Boiling point:", f"{rng.randint(50,300)}°C"],
        ["Vapour pressure:", f"{round(rng.uniform(0.1,100),1)} hPa (20°C)"],
        ["Vapour density:", f"{round(rng.uniform(0.5,5.0),1)} (air=1)"],
        ["Relative density:", f"{round(rng.uniform(0.7,1.8),3)} (water=1, 20°C)"],
        ["Solubility:", rng.choice(["Miscible with water", "Slightly soluble", "Insoluble in water", "Soluble in ethanol"])],
        ["Log Kow:", f"{round(rng.uniform(-2,6),2)}"],
        ["Viscosity:", f"{round(rng.uniform(0.5,50),1)} mPa·s (20°C)"],
    ], story)

    _section("SECTION 10 — STABILITY AND REACTIVITY", story, h1)
    _kv_table([
        ["Reactivity:", "No dangerous reactions under normal conditions of use."],
        ["Chemical stability:", "Stable under recommended storage conditions."],
        ["Hazardous reactions:", "May react vigorously with " + rng.choice(["oxidising agents","strong acids","water","bases"]) + "."],
        ["Conditions to avoid:", rng.choice(["Heat, sparks, open flames", "Moisture", "Light", "High temperatures"])],
        ["Hazardous decomposition:", rng.choice(["CO, CO₂, NOₓ", "HCl gas", "SO₂", "Formaldehyde vapour"])],
    ], story)

    _section("SECTION 11 — TOXICOLOGICAL INFORMATION", story, h1)
    _kv_table([
        ["LD50 (oral, rat):", f"{rng.randint(50,5000)} mg/kg"],
        ["LD50 (dermal, rabbit):", f"{rng.randint(200,5000)} mg/kg"],
        ["LC50 (inhalation, rat, 4h):", f"{round(rng.uniform(0.5,50),1)} mg/L"],
        ["Skin sensitisation:", rng.choice(["Not a skin sensitiser", "May cause sensitisation by skin contact"])],
        ["Mutagenicity:", rng.choice(["Not genotoxic in standard battery tests", "Positive — Ames test (S. typhimurium TA100)"])],
        ["Carcinogenicity:", rng.choice(["Not classified", "IARC Group 2B — possibly carcinogenic to humans"])],
        ["STOT — single exposure:", f"May cause {rng.choice(['drowsiness','respiratory irritation','narcotic effects'])} (Category {rng.randint(1,3)})."],
    ], story)
    story.append(PageBreak())

    _section("SECTION 12 — ECOLOGICAL INFORMATION", story, h1)
    _kv_table([
        ["Aquatic toxicity (LC50 fish, 96h):", f"{round(rng.uniform(0.1,100),2)} mg/L"],
        ["Aquatic toxicity (EC50 daphnia, 48h):", f"{round(rng.uniform(0.5,50),2)} mg/L"],
        ["Aquatic toxicity (ErC50 algae, 72h):", f"{round(rng.uniform(0.1,30),2)} mg/L"],
        ["Persistence:", rng.choice(["Readily biodegradable (>60% BOD 28 days)", "Not readily biodegradable", "Persistent"])],
        ["Bioaccumulation:", f"BCF: {rng.randint(10,500)} — {'Not expected to bioaccumulate' if rng.random()>0.3 else 'Potential to bioaccumulate'}"],
        ["Mobility in soil:", rng.choice(["High mobility", "Low to moderate mobility", "Immobile"])],
    ], story)

    _section("SECTION 13 — DISPOSAL CONSIDERATIONS", story, h1)
    story.append(Paragraph(
        "Dispose of in accordance with local regulations. Do not discharge to sewers. "
        "Contact a licensed waste disposal company. "
        f"EWC waste code: {rng.randint(10,20)} {rng.randint(10,20)} {rng.randint(10,20):02d}*.", body))

    _section("SECTION 14 — TRANSPORT INFORMATION", story, h1)
    un_no = rng.randint(1000, 3500)
    _kv_table([
        ["UN Number:", f"UN{un_no}"],
        ["UN Proper Shipping Name:", f"{chem.name.upper()} SOLUTION"],
        ["Hazard Class:", f"{rng.choice(['3','6.1','8','9'])}"],
        ["Packing Group:", rng.choice(["I", "II", "III"])],
        ["Marine Pollutant:", rng.choice(["Yes", "No"])],
        ["Special Precautions:", "See Section 7."],
    ], story)

    _section("SECTION 15 — REGULATORY INFORMATION", story, h1)
    _kv_table([
        ["SARA 311/312 Hazard Class:", rng.choice(["Immediate health", "Delayed health", "Fire hazard"])],
        ["SARA 313 Reporting:", rng.choice(["Not listed", f"CAS {chem.cas_number} is listed"])],
        ["TSCA Status:", "Listed on TSCA Chemical Substance Inventory"],
        ["REACH Registration:", f"Reg. No. 01-{rng.randint(1000000000000,9999999999999)}-{rng.randint(10,99)}-{rng.randint(1000,9999)}"],
        ["EU Classification:", rng.choice(["Flam. Liq. 2; H225", "Acute Tox. 4; H302", "Skin Irrit. 2; H315"])],
        ["California Prop 65:", rng.choice(["Not listed", "WARNING: This product contains chemicals known to CA to cause cancer."])],
    ], story)

    _section("SECTION 16 — OTHER INFORMATION", story, h1)
    story.append(Paragraph(
        f"Prepared by: {rng.choice(['EHS Department','Safety Officer','Regulatory Affairs'])} | "
        f"Issue date: {datetime.date.today().isoformat()} | "
        f"Supersedes: {(datetime.date.today() - datetime.timedelta(days=rng.randint(180,730))).isoformat()}", body))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "The information contained herein is believed to be accurate as of the date of publication. "
        "It is the user's responsibility to determine the suitability of this information for their "
        "particular use. No warranty, expressed or implied, is made.", body))

    doc.build(story, onFirstPage=_page_num, onLaterPages=_page_num)
