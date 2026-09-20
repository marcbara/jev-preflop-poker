#!/usr/bin/env python3
"""Poker primitives for the Jev preflop study.

Deterministic, reproducible:
  - all 169 hand classes (13 pairs + 78 suited + 78 offsuit)
  - a range-notation parser ("22+", "A2s+", "KTo+", ...)
  - four reference players (NIT / TAG / LAG / GTO) as open ranges per
    position and as (3-bet, call) ranges vs an UTG raise.

Everything here is code, not an LLM: the baselines are fixed functions
over the 169 combos.
"""

RANKS = list("23456789TJQKA")
RANK_IDX = {r: i for i, r in enumerate(RANKS)}

RANK_NAME = {'2': 'two', '3': 'three', '4': 'four', '5': 'five',
             '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
             'T': 'ten', 'J': 'jack', 'Q': 'queen', 'K': 'king',
             'A': 'ace'}

POSITION_LABEL = {
    'UTG': 'under the gun (UTG, first to act)',
    'CO': 'in the cutoff (CO)',
    'BTN': 'on the button (BTN)',
    'BB': 'in the big blind (BB)',
}


def all_hands():
    """Return the 169 hand classes as (high_idx, low_idx, type)."""
    hands = []
    for i in range(13):
        hands.append((i, i, 'p'))
        for j in range(i + 1, 13):
            hands.append((j, i, 's'))
            hands.append((j, i, 'o'))
    return hands


def name(h):
    """Standard notation: 'AA', 'A5s', 'KJo'."""
    hi, lo, t = h
    h, l = RANKS[hi], RANKS[lo]
    if t == 'p':
        return h + h
    return h + l + t


def expand(h):
    """Plain-language expansion: 'A5s (ace-five suited)'."""
    n = name(h)
    hi, lo, t = h
    h, l = RANKS[hi], RANKS[lo]
    if t == 'p':
        return "%s (a pair of %ss)" % (n, RANK_NAME[h])
    return "%s (%s-%s %s)" % (n, RANK_NAME[h], RANK_NAME[l],
                              'suited' if t == 's' else 'offsuit')


def weight(h):
    """Combinatorial weight: pairs 6, suited 4, offsuit 12."""
    return {'p': 6, 's': 4, 'o': 12}[h[2]]


TOTAL_COMBOS = 1326


def parse_range(spec):
    """Expand range notation into a set of hand classes."""
    result = set()
    for tok in spec.split(','):
        tok = tok.strip()
        if not tok:
            continue
        if tok.endswith('+'):
            base = tok[:-1]
            if len(base) == 2 and base[0] == base[1]:  # "22+", "JJ+"
                r = RANK_IDX[base[0]]
                for i in range(r, 13):
                    result.add((i, i, 'p'))
            else:
                assert len(base) == 3 and base[2] in 'so', tok
                hi, lo, t = RANK_IDX[base[0]], RANK_IDX[base[1]], base[2]
                for kick in range(lo, hi):
                    result.add((hi, kick, t))
        else:
            if len(tok) == 2 and tok[0] == tok[1]:
                r = RANK_IDX[tok[0]]
                result.add((r, r, 'p'))
            else:
                assert len(tok) == 3, tok
                hi, lo, t = RANK_IDX[tok[0]], RANK_IDX[tok[1]], tok[2]
                result.add((hi, lo, t))
    return result


def range_pct(spec):
    """Combinatorial percentage of a range string (0-100)."""
    return 100.0 * sum(weight(h) for h in parse_range(spec)) / TOTAL_COMBOS


# ---------------------------------------------------------------------------
# Reference players: open ranges per position.
# Approximations of standard 6-max 100bb ranges. Documented for review.
# ---------------------------------------------------------------------------
OPEN_RANGES = {
    'NIT': {  # ultraconservador: same ~4-5% everywhere
        'UTG': "JJ+, AKs, AKo, AQs, AQo",
        'CO':  "JJ+, AKs, AKo, AQs, AQo",
        'BTN': "JJ+, AKs, AKo, AQs, AQo",
    },
    'TAG': {  # conservador (~17% UTG -> ~41% BTN)
        'UTG': "22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, ATo+, KJo+",
        'CO':  "22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "54s, A9o+, KTo+, QTo+, JTo, T9o",
        'BTN': "22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "53s+, 43s, A2o+, K9o+, Q9o+, J9o+, T9o, 98o, 87o, 76o",
    },
    'LAG': {  # agressiu: plays ~one position looser than TAG
        'UTG': "22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "54s, A9o+, KTo+, QTo+, JTo, T9o",
        'CO':  "22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "53s+, 43s, A2o+, K9o+, Q9o+, J9o+, T9o, 98o, 87o, 76o",
        'BTN': "22+, A2s+, K2s+, Q2s+, J5s+, T5s+, 95s+, 85s+, 74s+, 63s+, "
               "52s+, 42s+, 32s, A2o+, K7o+, Q8o+, J8o+, T8o+, 97o+, 86o+, "
               "75o+, 64o+, 53o+",
    },
    'GTO': {  # solver reference: open width ≈ TAG (documented approximation)
        'UTG': "22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, ATo+, KJo+",
        'CO':  "22+, A2s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "54s, A9o+, KTo+, QTo+, JTo, T9o",
        'BTN': "22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 86s+, 75s+, 64s+, "
               "53s+, 43s, A2o+, K9o+, Q9o+, J9o+, T9o, 98o, 87o, 76o",
    },
}

# ---------------------------------------------------------------------------
# Reference players: response to an UTG open-raise to 3bb (fold/call/3-bet).
# Defined per position as (threebet_range, call_range); everything else folds.
# ---------------------------------------------------------------------------
FACE_RANGES = {
    'NIT': {
        'BTN': ("AA, KK, AKs",
                "QQ, JJ, TT, AKo, AQs, AQo"),
        'BB':  ("AA, KK, AKs",
                "QQ, JJ, TT, AKo, AQs, AQo"),
    },
    'TAG': {
        'BTN': ("AA, KK, QQ, JJ, AKs, AKo, AQs, A5s, A4s",
                "TT, 99, 88, 77, 66, 55, 44, 33, 22, AQo, AJs, ATs, A9s, "
                "A8s, A7s, A6s, A3s, A2s, KQs, KJs, KTs, QJs, QTs, JTs, "
                "T9s, 98s, 87s, 76s, 65s, 54s"),
        'BB':  ("AA, KK, QQ, JJ, AKs, AKo",
                "TT, 99, 88, 77, 66, 55, 44, 33, 22, AQs, AQo, AJs, ATs, "
                "A9s, A8s, A7s, A6s, A5s, A4s, A3s, A2s, KQs, KJs, KTs, "
                "QJs, QTs, JTs, T9s, 98s, 87s, 76s, 65s, 54s, 43s"),
    },
    'LAG': {
        'BTN': ("AA, KK, QQ, JJ, TT, 99, AKs, AKo, AQs, AQo, AJs, AJo, ATs, "
                "KQs, KQo, A5s, A4s, A3s, A2s, KJs",
                "88, 77, 66, 55, 44, 33, 22, A9s, A8s, A7s, A6s, KTs, QJs, "
                "QTs, JTs, T9s, 98s, 87s, 76s, 65s, 54s, 43s"),
        'BB':  ("AA, KK, QQ, JJ, TT, 99, AKs, AKo, AQs, AQo",
                "88, 77, 66, 55, 44, 33, 22, AJs, ATs, A9s, A8s, A7s, A6s, "
                "A5s, A4s, A3s, A2s, KQs, KJs, KTs, QJs, QTs, JTs, T9s, "
                "98s, 87s, 76s, 65s, 54s, 43s, KQo, AJo, KJo"),
    },
    'GTO': {
        'BTN': ("AA, KK, QQ, JJ, TT, AKs, AKo, AQs, A5s, A4s, A3s, A2s, "
                "KQs, AQo, AJo, KQo",
                "99, 88, 77, 66, 55, 44, 33, 22, AJs, ATs, A9s, A8s, A7s, "
                "A6s, KJs, KTs, QJs, QTs, JTs, T9s, 98s, 87s, 76s, 65s, "
                "54s, ATo, KJo"),
        'BB':  ("AA, KK, QQ, JJ, AKs, AKo, AQs, A5s, A4s, A3s, A2s",
                "TT, 99, 88, 77, 66, 55, 44, 33, 22, AQo, AJs, ATs, A9s, "
                "A8s, A7s, A6s, KQs, KJs, KTs, QJs, QTs, JTs, T9s, 98s, "
                "87s, 76s, 65s, 54s, 43s, ATo, KJo"),
    },
}


def open_action(player, hand, position):
    """fold/call/raise for an unopened pot (folded to hero)."""
    rng = parse_range(OPEN_RANGES[player][position])
    return 'raise' if hand in rng else 'fold'


def face_action(player, hand, position):
    """fold/call/raise (3-bet) facing an UTG raise to 3bb."""
    threebet, call = (parse_range(r) for r in FACE_RANGES[player][position])
    if hand in threebet:
        return 'raise'
    if hand in call:
        return 'call'
    return 'fold'


def self_test():
    print("%-5s %-4s %7s" % ("player", "pos", "open%"))
    for p in OPEN_RANGES:
        for pos in ('UTG', 'CO', 'BTN'):
            print("%-5s %-4s %6.1f%%" % (p, pos,
                                         range_pct(OPEN_RANGES[p][pos])))
    print()
    print("%-5s %-4s %6s %6s" % ("player", "pos", "3bet%", "call%"))
    for p in FACE_RANGES:
        for pos in ('BTN', 'BB'):
            tb, ca = FACE_RANGES[p][pos]
            print("%-5s %-4s %5.1f%% %5.1f%%" % (p, pos,
                                                 range_pct(tb),
                                                 range_pct(ca)))


if __name__ == '__main__':
    self_test()
