#!/usr/bin/env python3
"""Regenerate publication-quality charts from data/battery.jsonl.

Clean solver-style range charts (raise=green, call=amber, fold=red) with
hand labels inside every cell, plus a tidy bar chart, determinism and
calibration plots. Overwrites out/*.png.
"""
import json
import os
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

import poker as P

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'battery.jsonl')
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'axes.edgecolor': '#c9cdd4',
    'axes.linewidth': 0.7,
    'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
})

# --- palette ----------------------------------------------------------
RAISE = '#4b8e6b'
CALL = '#c49a4a'
FOLD = '#c06b62'
NONE = '#eceef1'
GRID = '#ffffff'

CMAP = ListedColormap([FOLD, CALL, RAISE, NONE])   # 0=fold 1=call 2=raise 3=none
ACT_IDX = {'fold': 0, 'call': 1, 'raise': 2, None: 3}

PLAYER_COLORS = {
    'Jev': '#2563eb', 'NIT': '#94a3b8', 'TAG': '#10b981',
    'LAG': '#f59e0b', 'GTO': '#8b5cf6',
}

OPEN_POS = ['UTG', 'CO', 'BTN']
FACE_POS = ['BTN', 'BB']
PLAYERS = ['Jev', 'NIT', 'TAG', 'LAG', 'GTO']
ORDER = 'AKQJT98765432'

# --- data -------------------------------------------------------------
recs = [json.loads(l) for l in open(DATA)]
groups = defaultdict(list)
for r in recs:
    groups[(r['scenario'], r['position'], r['hand'])].append(r)
spots = {}
for k, rs in groups.items():
    scen, pos, hand = k
    c = [r['choice'] for r in rs if r.get('choice')]
    if c:
        spots[k] = Counter(c).most_common(1)[0][0]

HANDS = P.all_hands()
HAND_NAME = {P.name(h): h for h in HANDS}


def jev_action(scen, pos, n):
    return spots.get((scen, pos, n))


def build_grid(action_fn):
    """action_fn(hand_name) -> 'raise'/'call'/'fold'/None -> (action, name) grids."""
    n = 13
    act = np.full((n, n), None, dtype=object)
    nm = np.empty((n, n), dtype=object)
    for h in HANDS:
        hi, lo, t = h
        H, L = P.RANKS[hi], P.RANKS[lo]
        if t == 'p':
            r = c = 12 - hi
            s = H + H
        elif t == 's':
            r, c = 12 - hi, 12 - lo
            s = H + L + 's'
        else:
            r, c = 12 - lo, 12 - hi
            s = H + L + 'o'
        act[r, c] = action_fn(s)
        nm[r, c] = s
    return act, nm


def draw_range(ax, action_fn, title):
    act, nm = build_grid(action_fn)
    n = 13
    numeric = np.full((n, n), 3.0)
    for i in range(n):
        for j in range(n):
            numeric[i, j] = ACT_IDX.get(act[i, j], 3)
    ax.imshow(numeric, cmap=CMAP, vmin=0, vmax=3, interpolation='nearest')
    for i in range(n):
        for j in range(n):
            a = act[i, j]
            txt = nm[i, j] if a is not None else ''
            color = '#ffffff' if a == 'raise' else (
                '#7a4a00' if a == 'call' else ('#ffffff' if a == 'fold' else '#b9bec7'))
            ax.text(j, i, txt, ha='center', va='center',
                    fontsize=5.6, color=color, fontweight='bold')
    ax.set_xticks(range(n)); ax.set_xticklabels(list(ORDER), fontsize=7)
    ax.set_yticks(range(n)); ax.set_yticklabels(list(ORDER), fontsize=7)
    ax.set_xticks([x - 0.5 for x in range(1, n)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, n)], minor=True)
    ax.grid(which='minor', color=GRID, linewidth=0.9)
    ax.tick_params(which='both', length=0, labelsize=7)
    for sp in ax.spines.values():
        sp.set_color('#c9cdd4')
    ax.set_title(title, fontsize=10, pad=6)


def range_legend(fig):
    fig.legend(handles=[Patch(color=RAISE, label='raise / 3-bet'),
                        Patch(color=CALL, label='call'),
                        Patch(color=FOLD, label='fold')],
               loc='lower center', ncol=3, frameon=False, fontsize=10,
               bbox_to_anchor=(0.5, -0.01))


# --- open heatmaps ----------------------------------------------------
fig, axes = plt.subplots(len(PLAYERS), len(OPEN_POS),
                         figsize=(len(OPEN_POS) * 4.1, len(PLAYERS) * 4.1))
for i, pl in enumerate(PLAYERS):
    for j, pos in enumerate(OPEN_POS):
        ax = axes[i, j]
        if pl == 'Jev':
            fn = lambda n, p=pos: jev_action('open', p, n)
        else:
            fn = lambda n, p=pos, b=pl: P.open_action(b, HAND_NAME[n], p)
        draw_range(ax, fn, pos if i == 0 else '')
        if j == 0:
            ax.set_ylabel(pl, fontsize=13, rotation=0, labelpad=32,
                          va='center', color=PLAYER_COLORS[pl], fontweight='bold')
range_legend(fig)
fig.suptitle('Opening ranges (folded to hero)', fontsize=15, y=0.995)
fig.subplots_adjust(left=0.09, right=0.99, top=0.94, bottom=0.05,
                    wspace=0.12, hspace=0.28)
fig.savefig(os.path.join(OUT, 'open_heatmaps.png'), dpi=150,
            bbox_inches='tight')
plt.close(fig)

# --- face heatmaps ----------------------------------------------------
fig, axes = plt.subplots(len(PLAYERS), len(FACE_POS),
                         figsize=(len(FACE_POS) * 4.1, len(PLAYERS) * 4.1))
for i, pl in enumerate(PLAYERS):
    for j, pos in enumerate(FACE_POS):
        ax = axes[i, j]
        if pl == 'Jev':
            fn = lambda n, p=pos: jev_action('face', p, n)
        else:
            fn = lambda n, p=pos, b=pl: P.face_action(b, HAND_NAME[n], p)
        draw_range(ax, fn, pos if i == 0 else '')
        if j == 0:
            ax.set_ylabel(pl, fontsize=13, rotation=0, labelpad=32,
                          va='center', color=PLAYER_COLORS[pl], fontweight='bold')
range_legend(fig)
fig.suptitle('Facing a UTG raise to 3bb', fontsize=15, y=0.995)
fig.subplots_adjust(left=0.09, right=0.99, top=0.94, bottom=0.07,
                    wspace=0.12, hspace=0.28)
fig.savefig(os.path.join(OUT, 'face_heatmaps.png'), dpi=150,
            bbox_inches='tight')
plt.close(fig)

# --- open % bar chart -------------------------------------------------
BAR_COLORS = {
    'Jev': '#e4574f', 'NIT': '#d9e1ea', 'TAG': '#7f97b0',
    'GTO': '#4d6885', 'LAG': '#2f4258',
}
BAR_ORDER = ['Jev', 'NIT', 'TAG', 'GTO', 'LAG']

open_pct = {}
for pl in PLAYERS:
    open_pct[pl] = []
    for pos in OPEN_POS:
        if pl == 'Jev':
            tot = hit = 0
            for h in HANDS:
                w = P.weight(h)
                tot += w
                if jev_action('open', pos, P.name(h)) == 'raise':
                    hit += w
            v = 100 * hit / tot
        else:
            v = P.range_pct(P.OPEN_RANGES[pl][pos])
        open_pct[pl].append(v)

fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(OPEN_POS))
width = 0.15
for i, pl in enumerate(BAR_ORDER):
    offs = (i - 2) * width
    bars = ax.bar(x + offs, open_pct[pl], width, label=pl,
                  color=BAR_COLORS[pl], zorder=3)
    for bar, v in zip(bars, open_pct[pl]):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1.2,
                '%.0f' % v, ha='center', va='bottom', fontsize=9,
                color='#4b5563', fontweight='bold' if pl == 'Jev' else 'normal')
ax.set_ylabel('Open-raise % (combo-weighted)', fontsize=11, color='#374151')
ax.set_xticks(x); ax.set_xticklabels(OPEN_POS, fontsize=12, color='#1f2937')
ax.set_ylim(0, max(max(v) for v in open_pct.values()) * 1.18)
ax.spines[['top', 'right']].set_visible(False)
ax.spines[['left', 'bottom']].set_color('#c9cdd4')
ax.yaxis.grid(True, color='#eceff3', zorder=0)
ax.set_axisbelow(True)
ax.tick_params(colors='#4b5563')
ax.legend(frameon=False, ncol=5, loc='upper center', bbox_to_anchor=(0.5, -0.08),
          fontsize=10)
ax.set_title('Opening frequency by position', fontsize=14, pad=12,
             color='#111827')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'open_pct.png'), dpi=150, bbox_inches='tight')
plt.close(fig)

# --- determinism ------------------------------------------------------
dets = [Counter([r['choice'] for r in rs if r.get('choice')]).most_common(1)[0][1] / 5
        for rs in groups.values() if any(r.get('choice') for r in rs)]
det_counts = Counter(int(round(d * 5)) for d in dets)

fig, ax = plt.subplots(figsize=(6.5, 4))
labels = ['1/5', '2/5', '3/5', '4/5', '5/5']
vals = [det_counts.get(k, 0) for k in (1, 2, 3, 4, 5)]
colors = ['#d9e1ea', '#a9b8c8', '#7f97b0', '#4d6885', '#2f4258']
ax.bar(labels, vals, color=colors, zorder=3)
for bar, v in zip(ax.patches, vals):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 4, str(v), ha='center',
            fontsize=10, color='#4b5563')
ax.set_ylabel('spots', fontsize=11, color='#374151')
ax.set_title('Determinism: reps agreeing per spot (of 5)', fontsize=13,
             color='#111827')
ax.spines[['top', 'right']].set_visible(False)
ax.spines[['left', 'bottom']].set_color('#c9cdd4')
ax.yaxis.grid(True, color='#eceff3', zorder=0)
ax.set_axisbelow(True)
ax.tick_params(colors='#4b5563')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'determinism.png'), dpi=150)
plt.close(fig)

# --- calibration ------------------------------------------------------
bins = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
calib = []
for lo, hi in bins:
    correct = total = 0
    for (scen, pos, hname), rs in groups.items():
        confs = [r['confidence'] for r in rs if r.get('confidence') is not None]
        choices = [r['choice'] for r in rs if r.get('choice')]
        if not confs or not choices:
            continue
        conf = float(np.mean(confs))
        if not (lo <= conf < hi):
            continue
        j = Counter(choices).most_common(1)[0][0]
        ref = (P.open_action('GTO', HAND_NAME[hname], pos) if scen == 'open'
               else P.face_action('GTO', HAND_NAME[hname], pos))
        w = P.weight(HAND_NAME[hname])
        total += w
        if j == ref:
            correct += w
    calib.append(100 * correct / total if total else 0.0)

fig, ax = plt.subplots(figsize=(6.5, 4))
centers = [0.1, 0.3, 0.5, 0.7, 0.9]
ax.plot(centers, calib, 'o-', color='#e4574f', linewidth=2.2, markersize=7,
        zorder=3)
for xc, yc in zip(centers, calib):
    ax.text(xc, yc + 3, '%.0f%%' % yc, ha='center', fontsize=10,
            color='#4b5563')
ax.set_xlabel('Jev confidence', fontsize=11, color='#374151')
ax.set_ylabel('Accuracy vs GTO (%)', fontsize=11, color='#374151')
ax.set_ylim(0, 110)
ax.set_xticks(centers)
ax.set_xticklabels(['0–0.2', '0.2–0.4', '0.4–0.6', '0.6–0.8', '0.8–1.0'],
                  fontsize=10)
ax.spines[['top', 'right']].set_visible(False)
ax.spines[['left', 'bottom']].set_color('#c9cdd4')
ax.yaxis.grid(True, color='#eceff3', zorder=0)
ax.set_axisbelow(True)
ax.tick_params(colors='#4b5563')
ax.set_title('Jev confidence vs accuracy (calibration)', fontsize=13,
             color='#111827')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'calibration.png'), dpi=150)
plt.close(fig)

print('regenerated:', [f for f in sorted(os.listdir(OUT)) if f.endswith('.png')])
