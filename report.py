#!/usr/bin/env python3
"""Analyze the Jev preflop battery: metrics, tables (CSV + markdown), charts.

Reads data/battery.jsonl (must be complete) and writes everything under out/.
All percentages are combo-weighted (pairs 6, suited 4, offsuit 12) so Jev and
the baselines are compared on the same 1326-combo basis.
"""
import csv
import json
import os
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import poker as P

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'battery.jsonl')
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

PLAYERS = ['Jev', 'NIT', 'TAG', 'LAG', 'GTO']
OPEN_POS = ['UTG', 'CO', 'BTN']
FACE_POS = ['BTN', 'BB']

# ---------------------------------------------------------------- load
recs = [json.loads(l) for l in open(DATA)]
groups = defaultdict(list)
for r in recs:
    groups[(r['scenario'], r['position'], r['hand'])].append(r)

spots = {}  # (scen, pos, hand) -> {action, det, conf}
for k, rs in groups.items():
    scen, pos, hand = k
    choices = [r['choice'] for r in rs if r.get('choice')]
    if not choices:
        spots[k] = {'action': None, 'det': None, 'conf': None}
        continue
    c = Counter(choices)
    act, cnt = c.most_common(1)[0]
    spots[k] = {
        'action': act,
        'det': cnt / len(rs),                              # 5/5=1.0
        'conf': float(np.mean([r['confidence'] for r in rs
                               if r.get('confidence') is not None])),
    }

HANDS = P.all_hands()
HAND_NAME = {P.name(h): h for h in HANDS}


def jev_action(scen, pos, hname):
    return spots.get((scen, pos, hname), {}).get('action')


def wfrac(pred):
    """Combo-weighted fraction of the 169 hand classes satisfying pred."""
    tot = hit = 0
    for h in HANDS:
        w = P.weight(h)
        tot += w
        if pred(P.name(h)):
            hit += w
    return hit / tot


# ---------------------------------------------------------------- open %
print("open % ...")
rows = [['player'] + OPEN_POS]
for pl in PLAYERS:
    vals = []
    for pos in OPEN_POS:
        if pl == 'Jev':
            v = wfrac(lambda n, p=pos: jev_action('open', p, n) == 'raise')
        else:
            v = P.range_pct(P.OPEN_RANGES[pl][pos]) / 100.0
        vals.append(round(v * 100, 1))
    rows.append([pl] + vals)
open_pct = {r[0]: r[1:] for r in rows[1:]}


def write_table(name, header, data_rows, fmt=None):
    with open(os.path.join(OUT, name + '.csv'), 'w', newline='') as f:
        csv.writer(f).writerow(header)
        csv.writer(f).writerows(data_rows)
    with open(os.path.join(OUT, name + '.md'), 'w') as f:
        f.write('| ' + ' | '.join(map(str, header)) + ' |\n')
        f.write('|' + '|'.join(['---'] * len(header)) + '|\n')
        for row in data_rows:
            f.write('| ' + ' | '.join(map(str, row)) + ' |\n')


write_table('open_pct', ['player'] + OPEN_POS, rows)

# ---------------------------------------------------------------- face %
print("face % ...")
face_rows = [['player', 'pos', '3bet%', 'call%', 'fold%']]
for pl in PLAYERS:
    for pos in FACE_POS:
        if pl == 'Jev':
            three = wfrac(lambda n, p=pos: jev_action('face', p, n) == 'raise')
            call = wfrac(lambda n, p=pos: jev_action('face', p, n) == 'call')
            fold = wfrac(lambda n, p=pos: jev_action('face', p, n) == 'fold')
        else:
            three = P.range_pct(P.FACE_RANGES[pl][pos][0]) / 100.0
            call = P.range_pct(P.FACE_RANGES[pl][pos][1]) / 100.0
            fold = 1.0 - three - call
        face_rows.append([pl, pos, round(three * 100, 1),
                          round(call * 100, 1), round(fold * 100, 1)])
write_table('face_pct', face_rows[0], face_rows[1:])

# ---------------------------------------------------------------- agreement
print("agreement ...")
agree_rows = [['player', 'scenario', 'agreement%']]
for pl in ['NIT', 'TAG', 'LAG', 'GTO']:
    for scen, positions in (('open', OPEN_POS), ('face', FACE_POS)):
        tot = hit = 0
        for h in HANDS:
            w = P.weight(h)
            n = P.name(h)
            for p in positions:
                tot += w
                j = jev_action(scen, p, n)
                b = (P.open_action(pl, h, p) if scen == 'open'
                     else P.face_action(pl, h, p))
                if j == b:
                    hit += w
        agree_rows.append([pl, scen, round(100.0 * hit / tot, 1)])
write_table('agreement', agree_rows[0], agree_rows[1:])

# ---------------------------------------------------------------- determinism
print("determinism ...")
dets = [s['det'] for s in spots.values() if s['det'] is not None]
det_hist = Counter(round(d * 5) for d in dets)   # 5,4,3,2,1
det_rows = [['reps_agreeing', 'spots', 'pct']]
for k in sorted(det_hist, reverse=True):
    det_rows.append([k, det_hist[k], round(det_hist[k] / len(dets) * 100, 1)])
det_rows.append(['mean_determinism', round(np.mean(dets), 3), ''])
write_table('determinism', det_rows[0], det_rows[1:])

# ---------------------------------------------------------------- calibration
print("calibration ...")
# accuracy vs GTO baseline, binned by Jev confidence
bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
cal_rows = [['conf_bin', 'n_spots', 'accuracy_vs_GTO%']]
calib = []
for lo, hi in bins:
    correct = total = 0
    for (scen, pos, hname), s in spots.items():
        if s['conf'] is None or s['action'] is None:
            continue
        if not (lo <= s['conf'] < hi):
            continue
        ref = (P.open_action('GTO', HAND_NAME[hname], pos) if scen == 'open'
               else P.face_action('GTO', HAND_NAME[hname], pos))
        total += P.weight(HAND_NAME[hname])
        if s['action'] == ref:
            correct += P.weight(HAND_NAME[hname])
    acc = (100.0 * correct / total) if total else 0.0
    cal_rows.append(["%.1f-%.1f" % (lo, min(hi, 1.0)), total, round(acc, 1)])
    calib.append(((lo + hi) / 2, acc))
write_table('calibration', cal_rows[0], cal_rows[1:])

# ---------------------------------------------------------------- jev matrix
print("jev matrix ...")
with open(os.path.join(OUT, 'jev_matrix.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['hand', 'open_UTG', 'open_CO', 'open_BTN', 'face_BTN', 'face_BB'])
    for h in HANDS:
        n = P.name(h)
        w.writerow([n,
                    jev_action('open', 'UTG', n),
                    jev_action('open', 'CO', n),
                    jev_action('open', 'BTN', n),
                    jev_action('face', 'BTN', n),
                    jev_action('face', 'BB', n)])

# ================================================================ charts
print("charts ...")
C_RAISE = (0.13, 0.60, 0.33)
C_CALL = (0.95, 0.76, 0.05)
C_FOLD = (0.86, 0.32, 0.30)
C_NONE = (0.88, 0.88, 0.88)
ORDER = list('AKQJT98765432')  # A top -> 2 bottom


def action_color(a):
    return {'raise': C_RAISE, 'call': C_CALL, 'fold': C_FOLD}.get(a, C_NONE)


def draw_grid(ax, lookup, pos, scen):
    """lookup(hand_name) -> action string; draw 13x13."""
    n = 13
    arr = np.zeros((n, n, 3))
    for h in HANDS:
        hi, lo, t = h
        H, L = P.RANKS[hi], P.RANKS[lo]
        if t == 'p':
            row, col = 12 - hi, 12 - hi
            nm = H + H
        elif t == 's':
            row, col = 12 - hi, 12 - lo      # suited: upper-right
            nm = H + L + 's'
        else:
            row, col = 12 - lo, 12 - hi      # offsuit: lower-left
            nm = H + L + 'o'
        arr[row, col] = action_color(lookup(nm))
    ax.imshow(arr, interpolation='nearest')
    ax.set_xticks(range(13)); ax.set_xticklabels(ORDER, fontsize=6)
    ax.set_yticks(range(13)); ax.set_yticklabels(ORDER, fontsize=6)
    ax.set_title(pos, fontsize=9)
    ax.set_xticks([x - 0.5 for x in range(1, 13)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, 13)], minor=True)
    ax.grid(which='minor', color='white', linewidth=0.8)
    ax.tick_params(which='both', length=0)


# --- open heatmaps: rows = players, cols = positions
fig, axes = plt.subplots(len(PLAYERS), len(OPEN_POS),
                         figsize=(3.2 * len(OPEN_POS), 3.2 * len(PLAYERS)))
for i, pl in enumerate(PLAYERS):
    for j, pos in enumerate(OPEN_POS):
        ax = axes[i][j]
        if pl == 'Jev':
            lookup = lambda n, p=pos: jev_action('open', p, n)
        else:
            lookup = lambda n, p=pos, b=pl: P.open_action(b, HAND_NAME[n], p)
        draw_grid(ax, lookup, pos, 'open')
        if j == 0:
            ax.set_ylabel(pl, fontsize=11, rotation=0, labelpad=25)
fig.suptitle('Opening ranges (folded to hero): raise=green, fold=red, '
             'call=yellow', fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(OUT, 'open_heatmaps.png'), dpi=150)
plt.close(fig)

# --- face heatmaps
fig, axes = plt.subplots(len(PLAYERS), len(FACE_POS),
                         figsize=(3.2 * len(FACE_POS), 3.2 * len(PLAYERS)))
for i, pl in enumerate(PLAYERS):
    for j, pos in enumerate(FACE_POS):
        ax = axes[i][j]
        if pl == 'Jev':
            lookup = lambda n, p=pos: jev_action('face', p, n)
        else:
            lookup = lambda n, p=pos, b=pl: P.face_action(b, HAND_NAME[n], p)
        draw_grid(ax, lookup, pos, 'face')
        if j == 0:
            ax.set_ylabel(pl, fontsize=11, rotation=0, labelpad=25)
fig.suptitle('Facing a UTG raise to 3bb: 3-bet=green, call=yellow, fold=red',
             fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(OUT, 'face_heatmaps.png'), dpi=150)
plt.close(fig)

# --- open % bar chart
fig, ax = plt.subplots(figsize=(7, 4.5))
x = np.arange(len(OPEN_POS))
width = 0.15
for i, pl in enumerate(PLAYERS):
    vals = [open_pct[pl][j] for j in range(len(OPEN_POS))]
    ax.bar(x + (i - 2) * width, vals, width, label=pl)
ax.set_ylabel('Open-raise % (combo-weighted)')
ax.set_xticks(x); ax.set_xticklabels(OPEN_POS)
ax.legend()
ax.set_title('Opening frequency by position')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'open_pct.png'), dpi=150)
plt.close(fig)

# --- determinism histogram
fig, ax = plt.subplots(figsize=(6, 4))
labels = ['1/5', '2/5', '3/5', '4/5', '5/5']
counts = [det_hist.get(k, 0) for k in (1, 2, 3, 4, 5)]
ax.bar(labels, counts, color='#4d79a7')
ax.set_ylabel('spots')
ax.set_title('Jev determinism: fraction of 5 reps agreeing')
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'determinism.png'), dpi=150)
plt.close(fig)

# --- calibration curve
fig, ax = plt.subplots(figsize=(6, 4))
xs = [c[0] for c in calib]
ys = [c[1] for c in calib]
ax.plot(xs, ys, 'o-', color='#d9534f')
ax.set_xlabel('Jev confidence')
ax.set_ylabel('Accuracy vs GTO baseline (%)')
ax.set_title('Does Jev confidence track correctness?')
ax.set_ylim(0, 105)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'calibration.png'), dpi=150)
plt.close(fig)

print("WROTE:", sorted(os.listdir(OUT)))
print("headline open% Jev:", open_pct['Jev'])
