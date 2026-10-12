"""Procedural-density signal for cooking-ish video records.

Hypothesis H3 (see `docs/plan-2026-10-12.md`): the ratio of
imperative-cooking verbs to total word tokens in
`title + description + recipe_steps` separates "cooking-adjacent" from
"genuinely procedural" content better than the boolean `has_steps` flag.

Returns a value in `[0, 1]`:
  - 0.00 when no imperative-verb hit at all.
  - Ramps linearly up to 1.00 at `TARGET_RATIO` (one imperative verb per
    twenty word tokens, i.e. 5%). Saturates above that so pure
    recipe-step dumps do not blow out the score.
"""

from __future__ import annotations

import re

from specint.records import VideoRecord

IMPERATIVE_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "stir",
        "mix",
        "whisk",
        "fold",
        "beat",
        "blend",
        "combine",
        "chop",
        "slice",
        "dice",
        "mince",
        "grate",
        "zest",
        "peel",
        "trim",
        "heat",
        "warm",
        "preheat",
        "cook",
        "bake",
        "roast",
        "broil",
        "grill",
        "boil",
        "simmer",
        "fry",
        "saute",
        "sear",
        "braise",
        "poach",
        "steam",
        "pour",
        "drain",
        "rinse",
        "season",
        "sprinkle",
        "toss",
        "coat",
        "serve",
        "garnish",
        "rest",
        "cool",
        "let",
        "cover",
        "reduce",
        "deglaze",
        "melt",
        "sweat",
        "crush",
        "mash",
        "knead",
        "roll",
    }
)

TARGET_RATIO = 0.05  # 1 imperative verb per 20 word tokens == full score
_TOKEN_RE = re.compile(r"[A-Za-z]+")


def imperative_hits(text: str) -> int:
    if not text:
        return 0
    return sum(1 for tok in _TOKEN_RE.findall(text) if tok.lower() in IMPERATIVE_VERBS)


def procedural_density(record: VideoRecord) -> float:
    corpus_parts = [record.title or "", record.description or ""]
    corpus_parts.extend(record.recipe_steps or [])
    corpus = " ".join(corpus_parts)
    tokens = _TOKEN_RE.findall(corpus)
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok.lower() in IMPERATIVE_VERBS)
    if hits == 0:
        return 0.0
    ratio = hits / len(tokens)
    return min(1.0, ratio / TARGET_RATIO)
