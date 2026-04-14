"""
animated_flow.py — Animated GIF for Karpathy LLM-Wiki Manufacturing Demo.
Outputs: output/karpathy_wiki_flow.gif
Dependencies: matplotlib, Pillow, numpy
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.animation import FuncAnimation
import numpy as np
import os

# ─── Paths ────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUT_DIR, 'karpathy_wiki_flow.gif')

# ─── Animation constants ──────────────────────────────────────────────────────
TOTAL_FRAMES = 90
FPS = 5
plt.rcParams['animation.embed_limit'] = 100

# Scene boundaries (frame indices, inclusive start)
SCENE_STARTS = [0, 18, 36, 54, 72]
SCENE_ENDS   = [17, 35, 53, 71, 89]

# ─── Color palette ────────────────────────────────────────────────────────────
BG       = '#0d1117'
TEXT_W   = '#e6edf3'
TEXT_DIM = '#8b949e'
ORANGE   = '#e67e22'
GREEN    = '#27ae60'
PURPLE   = '#8e44ad'
BLUE     = '#3498db'
RED      = '#e74c3c'
YELLOW   = '#f39c12'
TEAL     = '#1abc9c'

PDF_COLORS = [ORANGE, BLUE, GREEN, PURPLE, TEAL, YELLOW, RED]

PDF_TYPES = [
    ('Equipment Specs',   80, ORANGE),
    ('Maintenance',       80, BLUE),
    ('QC Reports',        70, GREEN),
    ('Supplier Profiles', 65, PURPLE),
    ('FMEA / Risk',       60, TEAL),
    ('Process Docs',      80, YELLOW),
    ('Training',          65, RED),
]

WIKI_CARDS = [
    'CNC M042 — Specs',
    'Supplier Haas — Profile',
    'Line 4 QC Q1',
    'FMEA — Press M107',
    'Maintenance SOP L4',
    'Downtime Analysis Q1',
    'Spindle Replacement Guide',
    'Coolant Specs — All Lines',
    'Vendor Comparison 2024',
    'Emergency Shutdown Proc',
    'ISO 9001 Checklist',
    'Material Cert — Steel A36',
]

# ─── Figure / axes setup ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 8), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis('off')

# ─── Artist containers ───────────────────────────────────────────────────────
artists = []   # flat list of all artists, cleared each frame

def clear_artists():
    global artists
    for a in artists:
        try:
            a.remove()
        except Exception:
            pass
    artists = []


def add(a):
    artists.append(a)
    return a


# ─── Helpers ─────────────────────────────────────────────────────────────────

def text(x, y, s, **kw):
    kw.setdefault('color', TEXT_W)
    kw.setdefault('ha', 'center')
    kw.setdefault('va', 'center')
    kw.setdefault('fontsize', 10)
    t = ax.text(x, y, s, transform=ax.transData, **kw)
    add(t)
    return t


def box(x, y, w, h, fc=BLUE, ec='white', lw=1.2, alpha=1.0,
        label='', fontsize=9, text_color='white', radius=0.15):
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle=f'round,pad={radius * 0.3}',
                           facecolor=fc, edgecolor=ec,
                           linewidth=lw, alpha=alpha,
                           transform=ax.transData, zorder=3)
    ax.add_patch(patch)
    add(patch)
    if label:
        t = ax.text(x + w / 2, y + h / 2, label,
                    ha='center', va='center', fontsize=fontsize,
                    fontweight='bold', color=text_color,
                    transform=ax.transData, zorder=4,
                    multialignment='center')
        add(t)
    return patch


def arrow_h(x0, x1, y, color=TEXT_W, lw=1.5, label='', fontsize=8):
    a = ax.annotate('', xy=(x1, y), xytext=(x0, y),
                    xycoords='data', textcoords='data',
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw),
                    zorder=5)
    add(a)
    if label:
        t = ax.text((x0 + x1) / 2, y + 0.15, label,
                    ha='center', va='bottom', fontsize=fontsize,
                    color=color, transform=ax.transData)
        add(t)
    return a


def arrow_v(x, y0, y1, color=TEXT_W, lw=1.5, label='', fontsize=8):
    a = ax.annotate('', xy=(x, y1), xytext=(x, y0),
                    xycoords='data', textcoords='data',
                    arrowprops=dict(arrowstyle='->', color=color, lw=lw),
                    zorder=5)
    add(a)
    if label:
        t = ax.text(x + 0.15, (y0 + y1) / 2, label,
                    ha='left', va='center', fontsize=fontsize,
                    color=color, transform=ax.transData)
        add(t)
    return a


def scene_badge(scene_num, scene_total=5, title=''):
    t = ax.text(13.8, 0.25, f'{scene_num}/{scene_total}  {title}',
                ha='right', va='bottom', fontsize=7.5, color=TEXT_DIM,
                transform=ax.transData)
    add(t)


def title_bar(title, subtitle=''):
    t = ax.text(7, 7.65, title,
                ha='center', va='center', fontsize=15, fontweight='bold',
                color=TEXT_W, transform=ax.transData)
    add(t)
    if subtitle:
        s = ax.text(7, 7.25, subtitle,
                    ha='center', va='center', fontsize=10, color=TEXT_DIM,
                    transform=ax.transData)
        add(s)


def fade_alpha(frame, start, end, fade_frames=6):
    """Return 0→1 alpha for a fade-in during [start, end]."""
    if frame < start:
        return 0.0
    if frame >= start + fade_frames:
        return 1.0
    return (frame - start) / fade_frames


# ── PDF grid builder ─────────────────────────────────────────────────────────
PDF_COLS = 25
PDF_ROWS = 20
PDF_W, PDF_H = 0.28, 0.20
PDF_XSTART = 0.5
PDF_YSTART = 1.0

def pdf_positions():
    """Return list of (x, y, color_index) for 500 PDFs in grid."""
    pos = []
    type_idx = 0
    type_count = 0
    for i in range(500):
        col = i % PDF_COLS
        row = i // PDF_COLS
        x = PDF_XSTART + col * (PDF_W + 0.02)
        y = PDF_YSTART + row * (PDF_H + 0.03)
        # assign type based on cumulative counts
        while type_idx < len(PDF_TYPES) - 1 and type_count >= PDF_TYPES[type_idx][1]:
            type_idx += 1
            type_count = 0
        pos.append((x, y, type_idx))
        type_count += 1
    return pos

PDF_POS = pdf_positions()


# ══════════════════════════════════════════════════════════════════════════════
# SCENE DRAWING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def draw_scene1(frame):
    """Scene 1: 500 PDFs in Stage. frames 0–17."""
    f = frame  # 0-based within animation total

    # Title (fade in first 4 frames)
    alpha_title = min(1.0, f / 3)
    text(7, 7.65, 'Karpathy LLM-Wiki  |  Manufacturing Demo',
         fontsize=14, fontweight='bold', color=TEXT_W, alpha=alpha_title)
    text(7, 7.2, 'Step 1: 500 PDFs in Snowflake Stage',
         fontsize=10, color=TEXT_DIM, alpha=alpha_title)

    # Draw PDF types progressively
    # Each type appears in frames 2–16 (spread across 7 groups)
    types_visible = max(0, min(7, int((f - 2) / 2 + 1)))

    # Render visible PDFs
    type_cumulative = [0]
    for t_info in PDF_TYPES:
        type_cumulative.append(type_cumulative[-1] + t_info[1])

    for idx, (x, y, tidx) in enumerate(PDF_POS):
        if tidx < types_visible:
            _, _, col = PDF_TYPES[tidx]
            patch = FancyBboxPatch((x, y), PDF_W, PDF_H,
                                   boxstyle='round,pad=0.01',
                                   facecolor=col, edgecolor='none',
                                   alpha=0.8, transform=ax.transData, zorder=2)
            ax.add_patch(patch)
            add(patch)

    # Type labels (appear with each type)
    lx = 0.5
    for i, (lbl, cnt, col) in enumerate(PDF_TYPES):
        if i < types_visible:
            ty = 6.6 - i * 0.32
            t = ax.text(lx + 0.15, ty, f'▪ {lbl} ({cnt})',
                        ha='left', va='center', fontsize=8,
                        color=col, transform=ax.transData, fontweight='bold')
            add(t)

    # Bottom label
    if f >= 10:
        text(7, 0.4,
             '@MFG_STAGE — 500 PDFs  |  ~37,500 pages total',
             fontsize=9.5, color=ORANGE, fontweight='bold',
             bbox=dict(facecolor='#161b22', edgecolor=ORANGE,
                       alpha=0.9, pad=4, boxstyle='round,pad=0.4'))

    scene_badge(1, title='— 500 PDFs in Stage')


def draw_scene2(frame):
    """Scene 2: Parsing. frames 18–35."""
    f = frame - 18   # 0-based within scene (0–17)

    title_bar('Step 2: Parsing — AI_PARSE_DOCUMENT',
              'LAYOUT mode — preserves tables, OCR for images')
    scene_badge(2, title='— Parsing')

    # Dimmed PDF grid (all 500)
    for idx, (x, y, tidx) in enumerate(PDF_POS):
        _, _, col = PDF_TYPES[tidx]
        patch = FancyBboxPatch((x, y), PDF_W, PDF_H,
                               boxstyle='round,pad=0.01',
                               facecolor=col, edgecolor='none',
                               alpha=0.25, transform=ax.transData, zorder=2)
        ax.add_patch(patch)
        add(patch)

    # AI_PARSE_DOCUMENT box fades in
    alpha_box = min(1.0, f / 4)
    if alpha_box > 0:
        box(8.0, 4.5, 3.0, 1.2, fc=ORANGE, alpha=alpha_box,
            label='AI_PARSE_DOCUMENT\nLAYOUT mode', fontsize=10)

    # Scanning arrow animates left to right across PDF grid
    if f >= 3:
        scan_progress = min(1.0, (f - 3) / 10)
        scan_x = PDF_XSTART + scan_progress * (PDF_COLS * (PDF_W + 0.02))
        scan_line = ax.axvline(scan_x, color=ORANGE, lw=2, alpha=0.7,
                               ymin=0.1, ymax=0.95)
        add(scan_line)

    # RAW_DOCUMENTS table fills
    if f >= 6:
        rows_visible = min(500, int((f - 6) / 11 * 500))
        box(8.0, 2.8, 3.0, 1.4, fc='#161b22', ec=BLUE, alpha=0.95,
            label=f'RAW_DOCUMENTS\n{rows_visible} / 500 rows', fontsize=10)
        # Row bars
        for r in range(min(rows_visible, 8)):
            bar_y = 3.05 + r * 0.12
            bar_w = 2.4 * min(1.0, (rows_visible - r * 60) / 60)
            bar = FancyBboxPatch((8.15, bar_y), max(0, bar_w), 0.08,
                                 boxstyle='round,pad=0.005',
                                 facecolor=BLUE, alpha=0.6,
                                 transform=ax.transData, zorder=4)
            ax.add_patch(bar)
            add(bar)

        # Arrow scan → RAW_DOCUMENTS
        arrow_h(8.0, 8.0, 4.2, color=ORANGE, lw=2)

    # Progress counter
    if f >= 6:
        parsed = min(500, int((f - 6) / 11 * 500))
        text(10.5, 2.5, f'Parsing: {parsed} / 500',
             fontsize=9, color=ORANGE)


def draw_scene3(frame):
    """Scene 3: Wiki compilation. frames 36–53."""
    f = frame - 36   # 0-based within scene (0–17)

    title_bar('Step 3: Wiki Compilation — COMPLETE()',
              'Domain Schema Prompt → Structured Wiki Pages')
    scene_badge(3, title='— Wiki Compilation')

    # RAW_DOCUMENTS box
    alpha_raw = min(1.0, f / 3)
    box(0.6, 5.5, 3.0, 1.2, fc='#161b22', ec=BLUE, alpha=alpha_raw,
        label='RAW_DOCUMENTS\n500 rows', fontsize=10)

    # COMPLETE() box
    alpha_llm = min(1.0, max(0, (f - 2) / 4))
    if alpha_llm > 0:
        box(4.5, 5.5, 3.2, 1.2, fc=PURPLE, alpha=alpha_llm,
            label='COMPLETE()\n+ Domain Schema Prompt', fontsize=9.5)
        if alpha_llm > 0.3:
            arrow_h(3.6, 4.5, 6.1, color=BLUE, lw=2, label='plain_text', fontsize=8)

    # Wiki cards appear progressively
    pages_visible = max(0, min(len(WIKI_CARDS), int((f - 5) / 1.0)))
    card_cols = 4
    card_x_start = 8.0
    card_y_start = 6.4
    cw, ch = 1.35, 0.55
    for ci in range(pages_visible):
        cx = card_x_start + (ci % card_cols) * (cw + 0.08)
        cy = card_y_start - (ci // card_cols) * (ch + 0.12)
        box(cx, cy, cw, ch, fc='#1a3a2a', ec=GREEN, lw=1,
            label=WIKI_CARDS[ci], fontsize=5.8)

    # Counter
    if f >= 5:
        total_estimate = min(2000, int((f - 5) * 125))
        text(10.8, 4.8, f'Building wiki:\n{total_estimate} / ~2 000 pages',
             fontsize=9, color=GREEN, fontweight='bold')

    # Highlights
    if f >= 12:
        highlights = ['Cross-references built', 'Red flags flagged',
                      'Contradictions noted']
        for hi, hl in enumerate(highlights):
            alpha_h = min(1.0, (f - 12 - hi) / 2)
            if alpha_h > 0:
                text(4.2, 5.0 - hi * 0.35, f'✓ {hl}',
                     fontsize=8.5, color=TEAL, ha='left', alpha=alpha_h)

    # Final glow for WIKI_PAGES / WIKI_INDEX
    if f >= 15:
        alpha_g = min(1.0, (f - 15) / 2)
        box(8.0, 2.2, 2.5, 0.9, fc='#0d2818', ec=GREEN,
            alpha=alpha_g, lw=2.5, label='WIKI_PAGES', fontsize=10)
        box(10.8, 2.2, 2.5, 0.9, fc='#0d2818', ec=GREEN,
            alpha=alpha_g, lw=2.5, label='WIKI_INDEX', fontsize=10)
        if alpha_g > 0.5:
            text(11.05, 1.9, '~2 000 pages  |  ~2 000 index entries',
                 fontsize=8, color=GREEN)


def draw_scene4(frame):
    """Scene 4: Query flow. frames 54–71."""
    f = frame - 54   # 0-based within scene (0–17)

    title_bar('Step 4: Query Flow',
              'Two-lane routing: point lookup vs synthesis')
    scene_badge(4, title='— Query Flow')

    # Dimmed wiki background
    for ci in range(min(len(WIKI_CARDS), 8)):
        cx = 0.5 + (ci % 4) * 1.45
        cy = 6.8 - (ci // 4) * 0.65
        box(cx, cy, 1.35, 0.55, fc='#0a1f12', ec='#1a4a2a', lw=0.8,
            label=WIKI_CARDS[ci], fontsize=5.5)

    # Question bubble
    alpha_q = min(1.0, f / 3)
    if alpha_q > 0:
        q_text = ('Which machines had the most downtime\n'
                  'last quarter and correlate with their suppliers?')
        box(3.0, 4.5, 8.0, 1.1, fc='#161b22', ec=BLUE,
            alpha=alpha_q, label=q_text, fontsize=8.5)

    # Classify diamond
    if f >= 3:
        alpha_d = min(1.0, (f - 3) / 3)
        diamond = plt.Polygon(
            [[7, 3.8], [8.2, 3.2], [7, 2.6], [5.8, 3.2]],
            facecolor=YELLOW, edgecolor='white', linewidth=1.5,
            alpha=alpha_d, transform=ax.transData, zorder=4)
        ax.add_patch(diamond)
        add(diamond)
        t = ax.text(7, 3.2, 'Classify:\nsynthesis', ha='center', va='center',
                    fontsize=7.5, fontweight='bold', color='#1a1a1a',
                    alpha=alpha_d, transform=ax.transData, zorder=5)
        add(t)
        if alpha_d > 0.3:
            arrow_v(7, 4.5, 3.8, color=BLUE, lw=2)

    # WIKI_INDEX lookup
    if f >= 6:
        alpha_wi = min(1.0, (f - 6) / 3)
        box(5.2, 1.5, 2.8, 0.9, fc='#0d2818', ec=GREEN,
            alpha=alpha_wi, label='WIKI_INDEX\nlookup', fontsize=9)
        arrow_v(7, 2.6, 2.4, color=GREEN, lw=2)

    # Highlighted pages
    if f >= 9:
        alpha_p = min(1.0, (f - 9) / 3)
        pages_highlight = [
            'Line 4 Downtime Analysis',
            'Haas Supplier Profile',
            'Q1 Maintenance Report',
        ]
        for pi, pg in enumerate(pages_highlight):
            px = 1.0 + pi * 3.0
            box(px, 0.6, 2.6, 0.75, fc='#1a3a2a', ec=GREEN,
                lw=2, alpha=alpha_p, label=pg, fontsize=8)

    # COMPLETE + answer
    if f >= 12:
        alpha_c = min(1.0, (f - 12) / 3)
        box(9.2, 1.5, 3.5, 0.9, fc=PURPLE, alpha=alpha_c,
            label='COMPLETE() + context', fontsize=9)
        arrow_h(8.0, 9.2, 1.95, color=GREEN, lw=2)

    if f >= 15:
        alpha_a = min(1.0, (f - 15) / 2)
        answer = ('Machine M042 (Haas): 47 hr downtime.\n'
                  'Spindle delay from Haas. FMEA sev. 8 flag active.')
        box(7.5, 0.4, 5.8, 0.95, fc='#1a1e2a', ec=BLUE,
            lw=2, alpha=alpha_a, label=answer, fontsize=8.5)
        text(7.5, 0.1,
             'Sources: 3 wiki pages  |  4 original PDFs  |  Synthesis lane  |  2.3s',
             fontsize=7.5, color=TEXT_DIM, ha='left', alpha=alpha_a)


def draw_scene5(frame):
    """Scene 5: Incremental update. frames 72–89."""
    f = frame - 72   # 0-based within scene (0–17)

    title_bar('Step 5: Incremental Update',
              'New PDF arrives — only delta processed')
    scene_badge(5, title='— Incremental')

    # Existing wiki (dimmed)
    for ci in range(min(len(WIKI_CARDS), 12)):
        cx = 8.2 + (ci % 3) * 1.85
        cy = 6.6 - (ci // 3) * 0.75
        is_affected = ci in (1, 5, 0)
        fc = '#1a3a2a' if not is_affected else '#0d2818'
        ec = '#2a5a3a' if not is_affected else GREEN
        lw = 0.8 if not is_affected else 2.5
        box(cx, cy, 1.7, 0.6, fc=fc, ec=ec, lw=lw,
            label=WIKI_CARDS[ci], fontsize=6)

    # New PDF drops in
    alpha_pdf = min(1.0, f / 3)
    pdf_y = max(4.5, 8.0 - f * 0.2) if f < 10 else 4.5
    box(2.0, pdf_y, 4.0, 0.9, fc='#1a1e2a', ec=ORANGE,
        lw=2.5, alpha=alpha_pdf,
        label='maintenance_report_Q2_2025.pdf', fontsize=9)

    # PARSE skips
    if f >= 4:
        alpha_s = min(1.0, (f - 4) / 3)
        box(0.5, 3.2, 5.5, 0.85, fc='#1a1e2a', ec=TEXT_DIM,
            lw=1, alpha=alpha_s,
            label='PARSE_NEW_DOCUMENTS() — skips 500 existing files', fontsize=8.5)
        arrow_v(4.0, 4.5, 4.05, color=ORANGE, lw=2)

    # AI_PARSE one file
    if f >= 7:
        alpha_p = min(1.0, (f - 7) / 3)
        box(0.5, 1.8, 5.5, 0.85, fc='#1a1e2a', ec=ORANGE,
            lw=1.5, alpha=alpha_p,
            label='AI_PARSE_DOCUMENT  (1 file only)', fontsize=9)
        arrow_v(4.0, 3.2, 2.65, color=ORANGE, lw=2)

    # Version bumps on affected wiki pages
    if f >= 10:
        alpha_v = min(1.0, (f - 10) / 3)
        bumps = [('M042 Maintenance', 'v2'), ('Line 4 Downtime', 'v3'),
                 ('Haas Supplier', 'v2')]
        for bi, (pg, ver) in enumerate(bumps):
            bx = 8.2 + (bi % 3) * 1.85
            by = 6.6 - 0.75  # second row
            box(bx, by, 1.7, 0.6, fc='#0d3020', ec=GREEN,
                lw=2.5, alpha=alpha_v, label=pg, fontsize=6.5)
            t = ax.text(bx + 1.55, by + 0.48, ver,
                        ha='right', va='top', fontsize=7,
                        color=GREEN, fontweight='bold', alpha=alpha_v,
                        transform=ax.transData,
                        bbox=dict(facecolor='#0a2010', edgecolor=GREEN,
                                  alpha=0.9, pad=1.5,
                                  boxstyle='round,pad=0.15'))
            add(t)

    # Big summary labels
    if f >= 13:
        alpha_fin = min(1.0, (f - 13) / 3)
        text(4.0, 0.9, '497 wiki pages unchanged',
             fontsize=13, fontweight='bold', color=GREEN, alpha=alpha_fin)
        text(4.0, 0.4,
             'Only delta processed — no full re-index needed',
             fontsize=9, color=TEXT_DIM, alpha=alpha_fin, style='italic')


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION UPDATE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

SCENE_FNS = [draw_scene1, draw_scene2, draw_scene3, draw_scene4, draw_scene5]


def update(frame):
    clear_artists()
    ax.set_facecolor(BG)

    # Determine current scene
    scene = 0
    for i, start in enumerate(SCENE_STARTS):
        if frame >= start:
            scene = i

    SCENE_FNS[scene](frame)
    return []


# ══════════════════════════════════════════════════════════════════════════════
# BUILD & SAVE
# ══════════════════════════════════════════════════════════════════════════════

print("Building animation…")
anim = FuncAnimation(fig, update, frames=TOTAL_FRAMES,
                     interval=1000 // FPS, blit=False, repeat=True)

print(f"Saving GIF to {OUTPUT_PATH} …")
anim.save(OUTPUT_PATH, writer='pillow', fps=FPS, dpi=100)
plt.close(fig)
print(f"Saved: {OUTPUT_PATH}")
