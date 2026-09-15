"""Curated lexicons used by metadata-only quality heuristics.

Kept in a separate file so tests can reason about lexicon growth
independently of the scoring math.
"""

from __future__ import annotations

# High-signal cooking imperative verbs. Deliberately English-only for
# this iteration (see H3 risk in `docs/plan-2026-09-15.md`).
COOKING_IMPERATIVE_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "brush",
        "caramelize",
        "chill",
        "chop",
        "combine",
        "cool",
        "cover",
        "cream",
        "crush",
        "cube",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "drizzle",
        "fold",
        "fry",
        "garnish",
        "glaze",
        "grate",
        "grease",
        "grill",
        "heat",
        "julienne",
        "knead",
        "layer",
        "marinate",
        "mash",
        "melt",
        "mince",
        "mix",
        "peel",
        "pinch",
        "poach",
        "pour",
        "preheat",
        "press",
        "puree",
        "reduce",
        "rest",
        "roast",
        "roll",
        "saute",
        "sauté",
        "scoop",
        "sear",
        "season",
        "serve",
        "shred",
        "sift",
        "simmer",
        "skim",
        "slice",
        "spread",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "stuff",
        "temper",
        "toast",
        "toss",
        "whip",
        "whisk",
        "wrap",
        "zest",
    }
)


def is_cooking_verb(token: str) -> bool:
    return token.lower() in COOKING_IMPERATIVE_VERBS
