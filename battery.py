#!/usr/bin/env python3
"""Full Jev preflop battery.

Pinned model, 169 hand classes, 5 reps per spot, incremental JSONL output
so a partial run is never lost. Appends to data/battery.jsonl.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from poker import (all_hands, name, expand, POSITION_LABEL,
                   TOTAL_COMBOS)

MODEL = "jev-1.13.0"          # pinned
REPS = 5
URL = "https://api.typesafe.ai/v1/systemone"

key = os.environ.get("TYPESAFE_API_KEY")
if not key:
    for line in open("/root/.hermes/.env"):
        if line.startswith("TYPESAFE_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
assert key, "no key (set TYPESAFE_API_KEY env var)"

QUESTION = {
    "action": {
        "type": "choice",
        "instructions": "Choose the best poker action in this situation",
        "criteria": {"fold": "fold", "call": "call", "raise": "raise"},
    }
}

OPEN_POS = ['UTG', 'CO', 'BTN']
FACE_POS = ['BTN', 'BB']

OPEN_TMPL = ("6-handed no-limit Texas hold'em cash game, all players 100 big "
             "blinds deep. It folds to you {pos}. Your hand: {hand}. You may "
             "fold, call (limp) the big blind, or raise. What is the correct "
             "action?")

FACE_TMPL = ("6-handed no-limit Texas hold'em cash game, all players 100 big "
             "blinds deep. UTG raises to 3 big blinds and it folds to you "
             "{pos}. Your hand: {hand}. You may fold, call, or re-raise. "
             "What is the correct action?")


def call_jev(state):
    body = json.dumps({"state": state, "model": MODEL,
                       "questions": QUESTION}).encode()
    req = urllib.request.Request(URL, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            return {"error": "HTTP %s" % e.code}
        except Exception as e:
            if attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            return {"error": str(e)}
    return {"error": "retries exhausted"}


out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "battery.jsonl")
os.makedirs(os.path.dirname(out_path), exist_ok=True)

hands = all_hands()

# build the spot list: (scenario, position, hand)
spots = []
for h in hands:
    for pos in OPEN_POS:
        spots.append(("open", pos, h))
    for pos in FACE_POS:
        spots.append(("face", pos, h))

total = len(spots) * REPS
done = 0
t0 = time.time()
errs = 0

with open(out_path, "a") as f:
    for (scen, pos, h) in spots:
        hname = name(h)
        if scen == "open":
            state = OPEN_TMPL.format(pos=POSITION_LABEL[pos], hand=expand(h))
        else:
            state = FACE_TMPL.format(pos=POSITION_LABEL[pos], hand=expand(h))
        for rep in range(REPS):
            r = call_jev(state)
            ans = r.get("answers", {}).get("action", {})
            rec = {
                "scenario": scen, "position": pos, "hand": hname,
                "rep": rep, "choice": ans.get("choice"),
                "probabilities": ans.get("probabilities"),
                "confidence": ans.get("confidence"),
                "model": r.get("model"),
                "error": r.get("error"),
                "ts": time.time(),
            }
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if r.get("error"):
                errs += 1
            done += 1
            if done % 250 == 0:
                rate = done / (time.time() - t0)
                eta = (total - done) / rate if rate else 0
                print("...%d/%d (%.1f/s, eta %.0fs, errs %d)"
                      % (done, total, rate, eta, errs), file=sys.stderr)
            time.sleep(0.05)

print("DONE total=%d errs=%d elapsed=%.0fs" % (done, errs,
                                               time.time() - t0))
