"""
flow_diagram.py — Static architecture diagram for Karpathy LLM-Wiki Manufacturing Demo.
Outputs: output/architecture.png (3600×2700 px)
Dependencies: matplotlib only
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# ─── Paths ────────────────────────────────────────────────────────────────────
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUT_DIR, 'architecture.png')

# ─── Colors ───────────────────────────────────────────────────────────────────
C_STAGE   = '#95a5a6'   # grey   — storage
C_AI      = '#e67e22'   # orange — AI functions
C_LLM     = '#8e44ad'   # purple — LLM / COMPLETE()
C_WIKI    = '#27ae60'   # green  — wiki tables
C_APP     = '#2980b9'   # blue   — application / RAW
C_ARROW   = '#2c3e50'   # dark   — arrows
C_BG      = '#fafafa'   # near-white background
C_PANEL   = '#ffffff'   # white panel
C_TEXT    = '#1a1a2e'   # near-black text

# ─── Figure ───────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(24, 18), dpi=150, facecolor=C_BG)
fig.patch.set_facecolor(C_BG)

# Three panels stacked vertically
ax1 = fig.add_axes([0.02, 0.60, 0.96, 0.38])   # top   40 %
ax2 = fig.add_axes([0.02, 0.31, 0.96, 0.27])   # mid   28 %
ax3 = fig.add_axes([0.02, 0.02, 0.96, 0.27])   # bot   28 %

for ax in (ax1, ax2, ax3):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    ax.set_facecolor(C_PANEL)
    for spine in ax.spines.values():
        spine.set_visible(False)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def rounded_box(ax, x, y, w, h, color, label, sublabel='', fontsize=9,
                text_color='white', alpha=1.0, zorder=3):
    """Draw a rounded rectangle with a centred label (and optional sublabel)."""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle='round,pad=0.01',
                         facecolor=color, edgecolor='white',
                         linewidth=1.5, alpha=alpha, zorder=zorder,
                         transform=ax.transAxes)
    ax.add_patch(box)
    cy = y + h / 2
    if sublabel:
        ax.text(x + w / 2, cy + h * 0.12, label,
                ha='center', va='center', fontsize=fontsize, fontweight='bold',
                color=text_color, transform=ax.transAxes, zorder=zorder + 1,
                clip_on=True)
        ax.text(x + w / 2, cy - h * 0.16, sublabel,
                ha='center', va='center', fontsize=fontsize - 1.5,
                color=text_color, transform=ax.transAxes, zorder=zorder + 1,
                clip_on=True, style='italic')
    else:
        ax.text(x + w / 2, cy, label,
                ha='center', va='center', fontsize=fontsize, fontweight='bold',
                color=text_color, transform=ax.transAxes, zorder=zorder + 1,
                clip_on=True)
    return box


def arrow(ax, x0, y0, x1, y1, label='', color=C_ARROW, lw=1.5,
          arrowstyle='->', fontsize=7.5):
    """Draw an annotated arrow between two axes-fraction coordinates."""
    ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle=arrowstyle, color=color,
                                lw=lw, connectionstyle='arc3,rad=0'))
    if label:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 0.025
        ax.text(mx, my, label, ha='center', va='bottom',
                fontsize=fontsize, color=color,
                transform=ax.transAxes,
                bbox=dict(facecolor=C_BG, edgecolor='none', alpha=0.7, pad=1))


def horiz_arrow(ax, x0, x1, y, label='', **kw):
    arrow(ax, x0, y, x1, y, label=label, **kw)


# ══════════════════════════════════════════════════════════════════════════════
# PANEL 1 — System Architecture
# ══════════════════════════════════════════════════════════════════════════════
ax = ax1
ax.set_facecolor('#f0f4f8')

ax.text(0.5, 0.96, 'Karpathy LLM-Wiki on Snowflake — System Architecture',
        ha='center', va='top', fontsize=14, fontweight='bold', color=C_TEXT,
        transform=ax.transAxes)

# Snowflake branding
ax.text(0.985, 0.96, '❄ Snowflake',
        ha='right', va='top', fontsize=11, color='#29B5E8', fontweight='bold',
        transform=ax.transAxes)

# ── Component positions (x, y, w, h) ─────────────────────────────────────────
BOX_H = 0.22
BOX_Y = 0.38   # vertical centre

coords = {
    'stage':     (0.01,  BOX_Y, 0.11, BOX_H),
    'parse':     (0.155, BOX_Y, 0.11, BOX_H),
    'raw':       (0.295, BOX_Y, 0.11, BOX_H),
    'complete':  (0.440, BOX_Y, 0.09, BOX_H),
    'wiki_p':    (0.565, BOX_Y + 0.06, 0.10, BOX_H * 0.45),
    'wiki_i':    (0.565, BOX_Y - 0.03, 0.10, BOX_H * 0.45),
    'answer':    (0.700, BOX_Y, 0.11, BOX_H),
    'streamlit': (0.855, BOX_Y, 0.11, BOX_H),
}

rounded_box(ax, *coords['stage'],   C_STAGE,  'Snowflake Stage', '@MFG_STAGE\n500 PDFs')
rounded_box(ax, *coords['parse'],   C_AI,     'AI_PARSE_DOCUMENT', 'LAYOUT mode')
rounded_box(ax, *coords['raw'],     C_APP,    'RAW_DOCUMENTS', 'Parsed text\n+ structure')
rounded_box(ax, *coords['complete'],C_LLM,    'COMPLETE()', '')
rounded_box(ax, *coords['wiki_p'],  C_WIKI,   'WIKI_PAGES',  fontsize=8)
rounded_box(ax, *coords['wiki_i'],  C_WIKI,   'WIKI_INDEX',  fontsize=8)
rounded_box(ax, *coords['answer'],  C_LLM,    'ANSWER_QUESTION', 'Two-lane routing',
            fontsize=8.5)
rounded_box(ax, *coords['streamlit'], '#1a252f', 'Streamlit App', 'SiS',
            fontsize=8.5)

# Helper to get right-edge centre and left-edge centre of a box
def rc(c): return c[0] + c[2], c[1] + c[3] / 2   # right-centre
def lc(c): return c[0],        c[1] + c[3] / 2   # left-centre
def tc(c): return c[0] + c[2] / 2, c[1] + c[3]   # top-centre
def bc(c): return c[0] + c[2] / 2, c[1]           # bot-centre

# ── Arrows ────────────────────────────────────────────────────────────────────
ax.annotate('', xy=lc(coords['parse']), xytext=rc(coords['stage']),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(0.13, BOX_Y + BOX_H / 2 + 0.03, 'per PDF', ha='center', fontsize=6.5,
        color=C_ARROW, transform=ax.transAxes)

ax.annotate('', xy=lc(coords['raw']), xytext=rc(coords['parse']),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(0.265, BOX_Y + BOX_H / 2 + 0.03, 'structured\nJSON', ha='center',
        fontsize=6, color=C_ARROW, transform=ax.transAxes)

ax.annotate('', xy=lc(coords['complete']), xytext=rc(coords['raw']),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(0.405, BOX_Y + BOX_H / 2 + 0.03, 'plain_text', ha='center',
        fontsize=6.5, color=C_ARROW, transform=ax.transAxes)

# COMPLETE → WIKI_PAGES and WIKI_INDEX (split arrows)
cx_r = coords['complete'][0] + coords['complete'][2]
cy_c = coords['complete'][1] + coords['complete'][3] / 2
ax.annotate('', xy=(coords['wiki_p'][0], coords['wiki_p'][1] + coords['wiki_p'][3] / 2),
            xytext=(cx_r, cy_c + 0.06),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(coords['wiki_i'][0], coords['wiki_i'][1] + coords['wiki_i'][3] / 2),
            xytext=(cx_r, cy_c - 0.04),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.text(0.532, BOX_Y + BOX_H / 2 + 0.09, 'compiled\nmarkdown', ha='center',
        fontsize=5.8, color=C_ARROW, transform=ax.transAxes)
ax.text(0.532, BOX_Y + BOX_H / 2 - 0.12, 'title +\nkeywords', ha='center',
        fontsize=5.8, color=C_ARROW, transform=ax.transAxes)

# WIKI_PAGES + WIKI_INDEX → ANSWER_QUESTION
for src in ('wiki_p', 'wiki_i'):
    ax.annotate('', xy=lc(coords['answer']),
                xytext=rc(coords[src]),
                xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.text(0.658, BOX_Y + BOX_H / 2 + 0.02, 'lookup', ha='center',
        fontsize=6.5, color=C_ARROW, transform=ax.transAxes)

ax.annotate('', xy=lc(coords['streamlit']), xytext=rc(coords['answer']),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))
ax.text(0.812, BOX_Y + BOX_H / 2 + 0.03, 'answer +\ncitations', ha='center',
        fontsize=6, color=C_ARROW, transform=ax.transAxes)

# ── Karpathy Layer brackets ───────────────────────────────────────────────────
def layer_bracket(ax, x0, x1, y, label, color):
    ax.annotate('', xy=(x1, y), xytext=(x0, y),
                xycoords='axes fraction', textcoords='axes fraction',
                arrowprops=dict(arrowstyle='<->', color=color, lw=2))
    ax.text((x0 + x1) / 2, y + 0.025, label, ha='center', va='bottom',
            fontsize=7, color=color, fontweight='bold',
            transform=ax.transAxes,
            bbox=dict(facecolor='white', edgecolor=color, alpha=0.85,
                      pad=2, boxstyle='round,pad=0.2'))

layer_bracket(ax, 0.01, 0.12, 0.17,  'Layer 1 — Raw Sources (@MFG_STAGE)', C_STAGE)
layer_bracket(ax, 0.565, 0.675, 0.17, 'Layer 2 — Wiki (WIKI_PAGES + WIKI_INDEX)', C_WIKI)

# Layer 3 label as a note
ax.text(0.44, 0.08,
        'Layer 3 — Schema: Domain prompt inside COMPILE_WIKI_PAGE SP',
        ha='center', va='bottom', fontsize=7.5, color=C_LLM,
        transform=ax.transAxes, style='italic',
        bbox=dict(facecolor='white', edgecolor=C_LLM, alpha=0.9,
                  pad=3, boxstyle='round,pad=0.3'))

# ── Legend ────────────────────────────────────────────────────────────────────
legend_items = [
    (C_STAGE,  'Stage / Storage'),
    (C_AI,     'AI Functions'),
    (C_LLM,    'LLM / COMPLETE()'),
    (C_WIKI,   'Wiki Tables'),
    (C_APP,    'Parsed Data / App'),
]
lx = 0.72
ly = 0.10
for i, (col, lbl) in enumerate(legend_items):
    patch = mpatches.Patch(facecolor=col, edgecolor='white', linewidth=0.5)
    ax.text(lx + i * 0.058, ly, '▪', color=col, fontsize=14,
            transform=ax.transAxes, va='center', ha='center')
    ax.text(lx + i * 0.058, ly - 0.07, lbl, color=C_TEXT, fontsize=5.5,
            transform=ax.transAxes, va='center', ha='center')


# ══════════════════════════════════════════════════════════════════════════════
# PANEL 2 — First Load Flow
# ══════════════════════════════════════════════════════════════════════════════
ax = ax2
ax.set_facecolor('#f8f9fa')

ax.text(0.5, 0.96, 'First Load — Building the Wiki from 500 PDFs',
        ha='center', va='top', fontsize=12, fontweight='bold', color=C_TEXT,
        transform=ax.transAxes)

# Swimlane dividers
lane_ys = [0.73, 0.44, 0.12]   # top of each lane (fraction)
lane_h  = 0.28
lane_labels = ['Upload', 'Parse', 'Compile']
lane_colors = [C_STAGE, C_AI, C_WIKI]

for i, (ly, ll, lc2) in enumerate(zip(lane_ys, lane_labels, lane_colors)):
    # Lane background stripe
    stripe = FancyBboxPatch((0.01, ly - lane_h + 0.02), 0.98, lane_h - 0.02,
                             boxstyle='round,pad=0.005',
                             facecolor=lc2, alpha=0.07, edgecolor=lc2,
                             linewidth=1, transform=ax.transAxes)
    ax.add_patch(stripe)
    # Lane label on left
    ax.text(0.005, ly - lane_h / 2 + 0.02, ll, ha='left', va='center',
            fontsize=9, fontweight='bold', color=lc2,
            transform=ax.transAxes, rotation=90)

def small_box(ax, x, y, w, h, color, label, fontsize=7.5):
    b = FancyBboxPatch((x, y), w, h,
                       boxstyle='round,pad=0.01',
                       facecolor=color, edgecolor='white',
                       linewidth=1.2, transform=ax.transAxes, zorder=3)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color='white',
            transform=ax.transAxes, zorder=4, wrap=True,
            multialignment='center')

# Lane 1 — Upload
small_box(ax, 0.10, 0.51, 0.18, 0.17, C_STAGE, '500 PDFs\ngenerated locally')
ax.annotate('', xy=(0.35, 0.60), xytext=(0.28, 0.60),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_STAGE, lw=2))
small_box(ax, 0.35, 0.51, 0.16, 0.17, C_STAGE, '@MFG_STAGE')
ax.text(0.31, 0.64, '~5 min', ha='center', fontsize=7.5, color=C_STAGE,
        transform=ax.transAxes, style='italic')

# Lane 2 — Parse
small_box(ax, 0.10, 0.22, 0.18, 0.17, C_AI, 'PARSE_NEW_\nDOCUMENTS()')
ax.annotate('', xy=(0.33, 0.305), xytext=(0.28, 0.305),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_AI, lw=2))
small_box(ax, 0.33, 0.22, 0.20, 0.17, C_AI, '500 ×\nAI_PARSE_DOCUMENT')
ax.annotate('', xy=(0.59, 0.305), xytext=(0.53, 0.305),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_AI, lw=2))
small_box(ax, 0.59, 0.22, 0.20, 0.17, C_APP, 'RAW_DOCUMENTS\n(500 rows)')
ax.text(0.50, 0.42, '~2–3 hrs  (parallel)', ha='center', fontsize=7.5,
        color=C_AI, transform=ax.transAxes, style='italic')

# Lane 3 — Compile
small_box(ax, 0.10, 0.03, 0.22, 0.17, C_LLM, 'COMPILE_WIKI_PAGE()\n× 500')
ax.annotate('', xy=(0.38, 0.115), xytext=(0.32, 0.115),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_LLM, lw=2))
small_box(ax, 0.38, 0.03, 0.18, 0.17, C_WIKI, 'WIKI_PAGES\n(~2 000 pages)')
ax.annotate('', xy=(0.62, 0.115), xytext=(0.56, 0.115),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_LLM, lw=2,
                            connectionstyle='arc3,rad=0'))
small_box(ax, 0.62, 0.03, 0.18, 0.17, C_WIKI, 'WIKI_INDEX\n(~2 000 entries)')
ax.text(0.50, 0.22, '~4–6 hrs  (parallel)', ha='center', fontsize=7.5,
        color=C_LLM, transform=ax.transAxes, style='italic')


# ══════════════════════════════════════════════════════════════════════════════
# PANEL 3 — Incremental Load + Query Flow
# ══════════════════════════════════════════════════════════════════════════════
ax = ax3
ax.set_facecolor('#f0f4f8')

ax.text(0.5, 0.97, 'Incremental Load & Query Flow',
        ha='center', va='top', fontsize=12, fontweight='bold', color=C_TEXT,
        transform=ax.transAxes)

# Divider between left (incremental) and right (query)
ax.plot([0.50, 0.50], [0.02, 0.93], color='#ced4da', linewidth=1.5,
        transform=ax.transAxes, zorder=1)

# ── LEFT HALF — Incremental ───────────────────────────────────────────────────
ax.text(0.25, 0.90, 'Incremental Load', ha='center', fontsize=9.5,
        fontweight='bold', color=C_WIKI, transform=ax.transAxes)

inc_steps = [
    (C_STAGE,  'New PDF arrives'),
    (C_AI,     'PARSE_NEW_DOCUMENTS()\nskips existing'),
    (C_AI,     'AI_PARSE_DOCUMENT\n(1 file)'),
    (C_LLM,    'COMPILE_WIKI_PAGE\n(1 doc)'),
    (C_WIKI,   'Affected WIKI_PAGES\nupdated'),
]
xs, ys = 0.08, 0.72
bw, bh = 0.34, 0.12
gap = 0.155
for i, (col, lbl) in enumerate(inc_steps):
    yy = ys - i * gap
    small_box(ax, xs, yy, bw, bh, col, lbl, fontsize=7)
    if i < len(inc_steps) - 1:
        ax.annotate('', xy=(xs + bw / 2, yy - 0.01),
                    xytext=(xs + bw / 2, yy + bh + 0.01),
                    xycoords='axes fraction', textcoords='axes fraction',
                    arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))

ax.text(0.25, 0.06,
        'Only delta processed — no full re-index',
        ha='center', va='center', fontsize=7.5, color=C_WIKI,
        fontweight='bold', style='italic', transform=ax.transAxes,
        bbox=dict(facecolor='#eafaf1', edgecolor=C_WIKI, alpha=0.9,
                  pad=3, boxstyle='round,pad=0.3'))

# ── RIGHT HALF — Query ────────────────────────────────────────────────────────
ax.text(0.75, 0.90, 'Query Flow', ha='center', fontsize=9.5,
        fontweight='bold', color=C_LLM, transform=ax.transAxes)

# User question
small_box(ax, 0.55, 0.76, 0.40, 0.12, C_APP, 'User Question', fontsize=8)

# Diamond classify
diamond_x, diamond_y = 0.75, 0.60
diamond_hw, diamond_hh = 0.10, 0.08
diamond = plt.Polygon(
    [[diamond_x, diamond_y + diamond_hh],
     [diamond_x + diamond_hw, diamond_y],
     [diamond_x, diamond_y - diamond_hh],
     [diamond_x - diamond_hw, diamond_y]],
    facecolor='#f39c12', edgecolor='white', linewidth=1.5,
    transform=ax.transAxes, zorder=3)
ax.add_patch(diamond)
ax.text(diamond_x, diamond_y, 'Classify?', ha='center', va='center',
        fontsize=7, fontweight='bold', color='white',
        transform=ax.transAxes, zorder=4)
ax.text(diamond_x - 0.13, diamond_y, 'point\nlookup', ha='center',
        fontsize=6, color='#f39c12', transform=ax.transAxes)
ax.text(diamond_x + 0.13, diamond_y, 'synthesis', ha='center',
        fontsize=6, color='#f39c12', transform=ax.transAxes)

# Arrow question → diamond
ax.annotate('', xy=(diamond_x, diamond_y + diamond_hh),
            xytext=(0.75, 0.76),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.5))

# Path 1 — Point lookup (left branch)
small_box(ax, 0.52, 0.38, 0.18, 0.10, C_APP, 'Cortex Search\n(WIKI_PAGES)', fontsize=7)
small_box(ax, 0.52, 0.26, 0.18, 0.10, C_APP, 'Top 3 pages', fontsize=7)
small_box(ax, 0.52, 0.14, 0.18, 0.10, C_LLM, 'COMPLETE()', fontsize=7)

ax.annotate('', xy=(0.61, 0.48), xytext=(diamond_x - diamond_hw, diamond_y),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2,
                            connectionstyle='arc3,rad=0.1'))
ax.annotate('', xy=(0.61, 0.38), xytext=(0.61, 0.48),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(0.61, 0.26), xytext=(0.61, 0.36),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(0.61, 0.14), xytext=(0.61, 0.24),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))

# Path 2 — Synthesis (right branch)
small_box(ax, 0.74, 0.38, 0.18, 0.10, C_WIKI, 'WIKI_INDEX\nlookup', fontsize=7)
small_box(ax, 0.74, 0.26, 0.18, 0.10, C_WIKI, '5 relevant\npages', fontsize=7)
small_box(ax, 0.74, 0.14, 0.18, 0.10, C_LLM,  'COMPLETE()', fontsize=7)

ax.annotate('', xy=(0.83, 0.48), xytext=(diamond_x + diamond_hw, diamond_y),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2,
                            connectionstyle='arc3,rad=-0.1'))
ax.annotate('', xy=(0.83, 0.38), xytext=(0.83, 0.48),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(0.83, 0.26), xytext=(0.83, 0.36),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(0.83, 0.14), xytext=(0.83, 0.24),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))

# Merge → Answer
small_box(ax, 0.57, 0.02, 0.36, 0.10, '#1a252f', 'Answer + Citations → Streamlit', fontsize=8)
ax.annotate('', xy=(0.61, 0.12), xytext=(0.61, 0.14),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))
ax.annotate('', xy=(0.83, 0.12), xytext=(0.83, 0.14),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=1.2))


# ══════════════════════════════════════════════════════════════════════════════
# Global title + footer
# ══════════════════════════════════════════════════════════════════════════════
fig.text(0.5, 0.993, 'Karpathy LLM-Wiki Manufacturing Demo — Architecture Overview',
         ha='center', va='top', fontsize=16, fontweight='bold', color=C_TEXT)
fig.text(0.5, 0.005,
         "Based on Karpathy's LLM-Wiki pattern: Layer 1 (raw sources) → Layer 2 (wiki) → Layer 3 (schema-constrained compilation). "
         "All compute runs inside Snowflake — no external orchestration needed.",
         ha='center', va='bottom', fontsize=7.5, color='#666666', style='italic')

# ── Save ──────────────────────────────────────────────────────────────────────
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight',
            facecolor=C_BG, edgecolor='none')
plt.close(fig)
print(f"Saved: {OUTPUT_PATH}")
