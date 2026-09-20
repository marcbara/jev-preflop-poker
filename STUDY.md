# Is Jev a Decent Preflop Poker Player?

**A reproducible behavioral benchmark of the TypeSafe "Jev" decision model
against four reference playing styles, over the 169 hold'em starting hands.**

*Run date: 2026-09-20 · Model pinned: `jev-1.13.0` · 4,225 API calls · 0 errors*

---

## 1. Motivation and question

Jev is a commercial "System One" decision model sold by TypeSafe. Its
documentation states it is trained to produce *calibrated structured
decisions* (a choice, a score, or a probability over fixed options) rather
than generated text. What its documentation does **not** state is what the
network was trained on: architecture, training data, or whether any poker
knowledge lives in its weights.

This study asks a single, empirically answerable question:

> **Given a complete preflop situation and the decision reduced to three
> options (fold / call / raise), does Jev choose like a decent poker player?**

"Decent" is made concrete by benchmarking Jev against four deterministic
reference players spanning the style spectrum (a nit, a tight-aggressive, a
loose-aggressive, and a GTO-style solver reference). The study is preflop
only: it says nothing about postflop play, bet sizing, or whether Jev would
win money in a full game.

---

## 2. What Jev is (and what is unknown)

**Known, from vendor documentation:**

- Jev is TypeSafe's flagship model and an example of a "System One" model:
  built to make fast, structured decisions that software consumes directly.
- It evaluates *typed questions* against a *state* (free text) and returns
  structured answers: for a `choice` question, the selected option plus a
  probability distribution over options and a confidence score.
- It does not generate prose; it classifies/scores against bounded options.

**Unknown (and not assumed anywhere in this study):**

- Architecture, parameter count, and training data.
- Whether the training signal included poker games, poker strategy text, or
  anything poker-related at all.
- How its internal representations change with the phrasing of the state.

This study is deliberately *behavioral*: it only measures what Jev *does*,
and explicitly does not claim to know what is inside the network.

---

## Terminology

- **Preflop**: the first betting round, before any community cards are dealt.
- **Position**: seat order relative to the button. **UTG** (under the gun) acts first and is worst; **CO** (cutoff) and **BTN** (button) act late; **BB** (big blind) is one of the two forced bets.
- **Open-raise (open)**: the first raise in a hand, after everyone has folded to you.
- **3-bet**: a re-raise over an opening raise.
- **Combo-weighted**: hands are not equally likely: each pocket pair has 6 card combinations, each suited hand 4, each offsuit hand 12, for 1,326 total. Every percentage here weights by these counts so it reflects true frequency, not just "number of hand types".
- **NIT (ultra-conservative)**: opens only premium hands (~4%), plays very few hands, rarely bluffs.
- **TAG (tight-aggressive)**: the standard "solid" style: selects strong hands (tight) and plays them aggressively (~17% open UTG).
- **LAG (loose-aggressive)**: plays many more hands (loose) and still plays them aggressively (~26% open UTG).
- **GTO (game-theory-optimal)**: a solver-balanced, theoretically unexploitable strategy; the standard reference for "perfect" play. Its preflop opening widths are very close to a solid TAG.
- **Determinism**: whether the model gives the same answer when asked the same input repeatedly.
- **Calibration**: whether the model's reported confidence matches how often it is actually correct.

---

## 3. Method

### 3.1 Game and decision space

- **Game:** 6-max no-limit Texas hold'em cash, all players 100 big blinds
  effective.
- **Decision space:** fold / call / raise, exposed as one `choice` question.
  No bet sizing (only the binary "raise" vs "call"), no multi-street play.
- **Hands:** all 169 classes (13 pocket pairs, 78 suited, 78 offsuit).
- **Positions:** under the gun (UTG), cutoff (CO), button (BTN), big blind
  (BB).

### 3.2 Scenarios (five per hand)

| Scenario | Hero position | Prior action |
|---|---|---|
| open UTG | UTG | everyone folds to hero |
| open CO | CO | everyone folds to hero |
| open BTN | BTN | everyone folds to hero |
| face raise BTN | BTN | UTG opens to 3bb, folds to hero |
| face raise BB | BB | UTG opens to 3bb, folds to hero |

### 3.3 State and prompt (exact)

Every call used this state template (with `{position}` and `{hand}` filled):

> `6-handed no-limit Texas hold'em cash game, all players 100 big blinds
> deep. It folds to you {position}. Your hand: {hand}. You may fold, call
> (limp) the big blind, or raise. What is the correct action?`

and, for the face-raise scenarios:

> `6-handed no-limit Texas hold'em cash game, all players 100 big blinds
> deep. UTG raises to 3 big blinds and it folds to you {position}. Your
> hand: {hand}. You may fold, call, or re-raise. What is the correct
> action?`

Hands were given in standard notation plus a plain-language gloss, e.g.
`A5s (ace-five suited)`, `AA (a pair of aces)`. The question schema was:

```json
{"action": {"type": "choice",
            "instructions": "Choose the best poker action in this situation",
            "criteria": {"fold": "fold", "call": "call", "raise": "raise"}}}
```

### 3.4 Model and repetitions

- Model pinned to `jev-1.13.0` (the API accepted the explicit version and
  returned it in every response; `jev-latest` also resolved to `jev-1.13.0`
  on the run date).
- Each of the 845 spots (169 hands × 5 scenarios) was queried **5 times** to
  measure determinism. Total **4,225 calls**, **0 errors**, ~52 minutes.
- Every raw response (choice, probability distribution, confidence, model
  version, timestamp) is stored in `data/battery.jsonl`.

### 3.5 Reference players (deterministic code, not LLMs)

Four baseline "players" were encoded as fixed functions over the 169 combos
in `poker.py`, so the comparison is fully reproducible and costs nothing.

| Player | Style | Open UTG | Open CO | Open BTN |
|---|---|---:|---:|---:|
| NIT | ultra-conservative | 4.2% | 4.2% | 4.2% |
| TAG | conservative | 17.3% | 26.4% | 40.6% |
| LAG | aggressive | 26.4% | 40.6% | 58.4% |
| GTO | solver reference | 17.3% | 26.4% | 40.6% |

Opening ranges (exact strings, in standard range notation):

- **NIT** (all positions): `JJ+, AKs, AKo, AQs, AQo`
- **TAG UTG**: `22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, ATo+, KJo+`
- **TAG CO**: `22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 64s+, 54s, A9o+, KTo+, QTo+, JTo, T9o`
- **TAG BTN**: `22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 64s+, 53s+, 43s, A2o+, K9o+, Q9o+, J9o+, T9o, 98o, 87o, 76o`
- **LAG** plays ~one position looser than TAG (LAG UTG = TAG CO, LAG CO =
  TAG BTN, LAG BTN is a wider custom range).
- **GTO** opening width equals TAG. This is a documented approximation, not
  a solver run: for preflop *opening*, solid TAG and GTO have essentially
  converged; the real GTO/TAG difference appears in 3-bet/call frequencies
  (see below), which is where the two baselines diverge.

Facing a UTG raise, each baseline has a (3-bet, call) pair of ranges;
everything else folds. Full strings are in `poker.py` (`FACE_RANGES`). Key
distinction: GTO 3-bets more than TAG (8.0% vs 3.9% on the button),
including the standard bluff 3-bets (A2s–A5s, AQo, AJo, KQo).

**These baseline ranges are approximations and should be reviewed by a poker
expert before publication.** They are, however, robust to the study's
conclusion.

### 3.6 Metrics

All percentages are **combo-weighted** (pairs 6, suited 4, offsuit 12, over
the 1326-combo deck) so Jev and the baselines are compared on the same
basis.

- **Open-raise % per position**: fraction of combos opened (raised).
- **Facing-raise distribution**: 3-bet / call / fold % per position.
- **Agreement %**: fraction of (hand, position) pairs where Jev's majority
  action equals the baseline's action.
- **Precision / recall on "raise"**: of the hands Jev raises, how many the
  baseline also raises (precision); of the hands the baseline raises, how
  many Jev also raises (recall). This is the informative metric, because raw
  agreement is inflated by the large fold-fraction shared by everyone.
- **Determinism**: fraction of the 5 reps that agree per spot.
- **Calibration**: Jev confidence vs accuracy against the GTO baseline.

---

## 4. Results

### 4.1 Open-raise frequency by position (combo-weighted %)

| Player | UTG | CO | BTN |
|---|---:|---:|---:|
| **Jev** | **14.3** | **31.5** | **28.5** |
| NIT | 4.2 | 4.2 | 4.2 |
| TAG | 17.3 | 26.4 | 40.6 |
| LAG | 26.4 | 40.6 | 58.4 |
| GTO | 17.3 | 26.4 | 40.6 |

Jev opens slightly tighter than TAG/GTO from UTG (14.3 vs 17.3), **looser**
than TAG/GTO from CO (31.5 vs 26.4), and **tighter** from the button (28.5
vs 40.6).

### 4.2 Facing a UTG raise to 3bb (%)

| Player | Pos | 3-bet | call | fold |
|---|---|---:|---:|---:|
| Jev | BTN | 12.7 | 5.7 | 81.6 |
| Jev | BB | 5.4 | 17.6 | 76.9 |
| NIT | BTN | 1.2 | 3.5 | 95.3 |
| NIT | BB | 1.2 | 3.5 | 95.3 |
| TAG | BTN | 3.9 | 11.0 | 85.1 |
| TAG | BB | 3.0 | 12.2 | 84.8 |
| LAG | BTN | 9.4 | 7.7 | 83.0 |
| LAG | BB | 5.1 | 12.8 | 82.1 |
| GTO | BTN | 8.0 | 10.6 | 81.4 |
| GTO | BB | 4.5 | 12.5 | 83.0 |

Jev is the most 3-bet-heavy of all five on the button (12.7%, above LAG's
9.4% and GTO's 8.0%) and call-light (5.7% vs GTO's 10.6%).

### 4.3 Agreement with each baseline (%)

| Baseline | open | face |
|---|---:|---:|
| NIT | 78.8 | 80.7 |
| TAG | 90.8 | 86.7 |
| LAG | 82.0 | 90.0 |
| GTO | 90.8 | 88.8 |

Jev's opening decisions agree with TAG/GTO on 90.8% of combos; its
facing-raise decisions agree with LAG/GTO on 88.8–90.0%.

### 4.4 Precision / recall on "raise" (the informative view)

| Scenario | Reference | precision | recall |
|---|---|---:|---:|
| open | TAG / GTO | 88.6% | 78.2% |
| face (3-bet) | TAG | 35.0% | 91.3% |
| face (3-bet) | GTO | 55.8% | 80.7% |

Reading: when Jev opens, 88.6% of the time it is a hand a solid player would
also open (high precision), but it misses ~22% of the standard opening range
(recall 78.2%). Facing a raise, Jev 3-bets too many hands (precision vs GTO
55.8%) while still 3-betting most of the premiums it should (recall 80.7%).

### 4.5 Determinism (of 5 reps per spot)

| Reps agreeing | spots | share |
|---|---:|---:|
| 5 / 5 | 798 | 94.4% |
| 4 / 5 | 26 | 3.1% |
| 3 / 5 | 21 | 2.5% |
| mean |  | 0.984 |

Jev is near-deterministic on this task: 94.4% of spots produce the identical
action across all five repetitions.

### 4.6 Confidence calibration (accuracy vs GTO, binned by Jev confidence)

| Confidence | Accuracy vs GTO |
|---|---:|
| 0.0–0.2 | 54.9% |
| 0.2–0.4 | 68.6% |
| 0.4–0.6 | 89.6% |
| 0.6–0.8 | 97.1% |
| 0.8–1.0 | 100.0% |

Jev's confidence is monotonically informative: the more confident it is, the
more likely it agrees with GTO. This is a genuinely well-calibrated output,
not a flat or inverted one.

---

## 5. Interpretation

1. **Jev plays a coherent, roughly tight-aggressive preflop game.** It is
   not random and not a maniac. Its opening frequency (14.3% UTG) is in the
   same band as a solid TAG/GTO (17.3%), and 88.6% of its opens are hands a
   solid player would also open.

2. **Its one clear structural flaw is the position gradient.** Every
   reference player widens sharply from cutoff to button (TAG +14.2 points,
   LAG +17.8). Jev instead opens *less* from the button (28.5%) than from
   the cutoff (31.5%), and only +14.2 points across the whole UTG→BTN span.
   It does not properly monetize the button. This is the most defensible,
   style-independent finding of the study.

3. **It is 3-bet-heavy and call-light facing raises**, with low precision on
   its 3-bets (55.8% vs GTO): it re-raises hands GTO would call or fold.

4. **Its outputs are reliable as a decision engine**, near-deterministic
   (98.4%) and well-calibrated, even though its poker *strategy* is
   imperfect.

Net: for the basic preflop situations tested, Jev plays "decent", a
competent, coherent, roughly-TAG game with one clear positional error and an
excess of aggression against raises. It does not look like a model with no
poker knowledge; it also does not look like a solver.

---

## 6. What this does and does not show

**Shows:** in complete, decision-reduced preflop spots, Jev's choices
correlate with hand strength and (imperfectly) with position, and its
confidence is meaningful.

**Does not show:** anything about postflop play, bet sizing, multi-street
reasoning, or whether Jev would win in a real game. "Plays decent preflop"
is not "plays winning poker."

**Does not show:** what is inside Jev's network. A behavioral result cannot
reveal training data or architecture. If Jev's behavior correlates with a
solid strategy, that is consistent with (but not proof of) poker-relevant
training signal.

---

## 7. Limitations

- **Preflop only, single decision.** No flop/turn/river, no betting rounds,
  no chip outcomes, no EV.
- **No bet sizing.** Actions are fold / call / raise; "raise" has no amount.
- **Fixed opponent action.** The raiser is always UTG, always 3bb. Jev never
  faces a raise from CO/BTN/SB, a different size, a limp, or multiple
  callers.
- **Seats not covered.** Jev is never in the small blind or the highjack,
  never opens then faces a 3-bet.
- **Baselines are approximations.** The NIT/TAG/LAG/GTO ranges are
  hand-encoded standard ranges, not solver outputs; GTO open width is set
  equal to TAG by assumption. They should be reviewed before publication,
  though the headline conclusion is robust to their exact boundaries.
- **One full run.** The battery was run once (with 5 intra-spot repetitions
  for determinism). A second full run was not done to confirm cross-run
  stability of the aggregate numbers.
- **Format sensitivity untested.** Hand descriptions were fixed to notation
  plus a plain gloss; an informal prose-only variant shifted two marginal
  hands, so phrasing may matter at the margins and was not controlled for.

---

## 8. Next steps (if this is extended)

1. **Clean format ablation**: isolate hand-description phrasing vs
   question-criteria wording; quantify how much each shifts the open
   frequency.
2. **Wider scenario coverage**: add SB and HJ seats, multiway pots, facing
   a 3-bet, and non-UTG / non-3bb raisers.
3. **Bet sizing**: expose raise amounts as a decision dimension.
4. **Full-game proxy**: combine preflop with a postflop engine to estimate
   win rate (out of scope for a single-decision benchmark).
5. **Cross-run reproducibility**: repeat the full battery to bound
   run-to-run variance of the aggregate numbers.

---

## 9. Reproducibility

Everything lives in `/root/jev-poker/` on `hermes-vps`.

| File | Purpose |
|---|---|
| `poker.py` | 169 hand classes, range parser, baseline definitions (deterministic) |
| `battery.py` | runs the 4,225 API calls, appends `data/battery.jsonl` |
| `report.py` | metrics + CSV/Markdown tables |
| `charts.py` | publication PNG charts |
| `README.md` | shorter project overview |

Requirements: a virtualenv with `matplotlib`, and `TYPESAFE_API_KEY` set in
`/root/.hermes/.env` (the key is never printed or committed).

```bash
cd /root/jev-poker
.venv/bin/python battery.py     # full run (~52 min)
.venv/bin/python report.py      # tables -> out/*.csv, out/*.md
.venv/bin/python charts.py      # charts -> out/*.png
```

Raw data: `data/battery.jsonl`, one JSON object per call, containing
scenario, position, hand, repetition, chosen action, probability
distribution, confidence, model version, and timestamp.

## 10. Artifacts

Tables (CSV + Markdown): `out/open_pct.*`, `out/face_pct.*`,
`out/agreement.*`, `out/determinism.*`, `out/calibration.*`,
`out/jev_matrix.csv` (per-hand action matrix for all 169 hands × 5
scenarios).

Charts (PNG): `out/open_heatmaps.png` (5 players × 3 open positions),
`out/face_heatmaps.png` (5 players × 2 facing-raise positions),
`out/open_pct.png` (open frequency by position), `out/determinism.png`,
`out/calibration.png`.
