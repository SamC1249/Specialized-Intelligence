"""Procedural-density scorer (metadata-only).

Cooking videos useful for world-model training are procedurally dense:
they say things like "chop 2 cloves of garlic, then sauté for 3 minutes
until golden". The v1 scorer (see `metrics.py`) is *format-agnostic*:
license + duration + resolution + text length + step presence. It
cannot distinguish "How to boil water — 45 minutes of chatter" from
"12-step béchamel with weights".

This module adds `procedural_density`, a v2 signal in [0, 1] computed
purely from the text on the record. It complements — does not replace —
the v1 signals. The `PROFILES` dict wires two named scorer profiles:

- `"v1"` (baseline): the existing WEIGHTS from `metrics.py`.
- `"v2_procedural"`: v1 + procedural_density weighted at 0.25 (v1
  components are re-normalised so weights sum to 1).

Design constraints:
- No external NLP deps. Only stdlib regex + curated lexicons.
- Multilingual lexicons for EN/ES/FR/DE/IT (matches search terms).
- Deterministic and pure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from specint.quality import metrics as v1
from specint.records import VideoRecord

IMPERATIVE_VERBS: dict[str, tuple[str, ...]] = {
    "en": (
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "chop",
        "combine",
        "cook",
        "cool",
        "cover",
        "cream",
        "cut",
        "dice",
        "drain",
        "drizzle",
        "dust",
        "fold",
        "fry",
        "garnish",
        "grate",
        "grease",
        "grill",
        "heat",
        "knead",
        "let",
        "marinate",
        "melt",
        "mince",
        "mix",
        "peel",
        "place",
        "pour",
        "preheat",
        "press",
        "reduce",
        "remove",
        "rinse",
        "roast",
        "roll",
        "saute",
        "sauté",
        "scoop",
        "season",
        "serve",
        "shred",
        "sift",
        "simmer",
        "slice",
        "spread",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "stuff",
        "taste",
        "toast",
        "toss",
        "transfer",
        "turn",
        "whip",
        "whisk",
    ),
    "es": (
        "añade",
        "agrega",
        "asa",
        "bate",
        "cocina",
        "corta",
        "cubre",
        "derrite",
        "desmenuza",
        "escurre",
        "espolvorea",
        "fríe",
        "hierve",
        "hornea",
        "incorpora",
        "mezcla",
        "pela",
        "pica",
        "precalienta",
        "reduce",
        "remueve",
        "rellena",
        "sirve",
        "sofríe",
        "tuesta",
        "vierte",
    ),
    "fr": (
        "ajoutez",
        "ajouter",
        "cuire",
        "chauffer",
        "hacher",
        "mélanger",
        "mettre",
        "mixer",
        "peler",
        "porter",
        "préchauffer",
        "réduire",
        "remuer",
        "réserver",
        "rôtir",
        "saler",
        "servir",
        "verser",
    ),
    "de": (
        "backen",
        "braten",
        "geben",
        "hinzufügen",
        "hacken",
        "kochen",
        "mischen",
        "pürieren",
        "reduzieren",
        "rühren",
        "schälen",
        "servieren",
        "vermischen",
        "vorheizen",
        "würzen",
    ),
    "it": (
        "aggiungi",
        "cuocere",
        "cuocere",
        "friggere",
        "mescolare",
        "preriscaldare",
        "servire",
        "sminuzzare",
        "soffriggere",
        "tagliare",
        "unire",
        "versare",
    ),
}

UNIT_TOKENS: tuple[str, ...] = (
    "tsp",
    "tsp.",
    "teaspoon",
    "teaspoons",
    "tbsp",
    "tbsp.",
    "tablespoon",
    "tablespoons",
    "cup",
    "cups",
    "pint",
    "pints",
    "quart",
    "quarts",
    "gallon",
    "gallons",
    "oz",
    "ounce",
    "ounces",
    "lb",
    "lbs",
    "pound",
    "pounds",
    "g",
    "gram",
    "grams",
    "kg",
    "kilogram",
    "kilograms",
    "ml",
    "milliliter",
    "milliliters",
    "millilitre",
    "millilitres",
    "l",
    "liter",
    "liters",
    "litre",
    "litres",
    "°c",
    "°f",
    "celsius",
    "fahrenheit",
    "minute",
    "minutes",
    "min",
    "mins",
    "hour",
    "hours",
    "hr",
    "hrs",
    "second",
    "seconds",
    "sec",
    "secs",
    "cucharadita",
    "cucharaditas",
    "cucharada",
    "cucharadas",
    "taza",
    "tazas",
    "gramo",
    "gramos",
    "mililitro",
    "mililitros",
    "litro",
    "litros",
    "cuillère",
    "cuillères",
    "gramme",
    "grammes",
    "litre",
    "litres",
    "tasse",
    "esslöffel",
    "teelöffel",
)

_QUANTITY_RE = __import__("re").compile(r"\b\d+(?:[.,/]\d+)?\b")
_TOKEN_RE = __import__("re").compile(r"[\w°]+", flags=0)


def _text_of(record: VideoRecord) -> str:
    parts = [record.title or "", record.description or ""]
    parts.extend(record.recipe_steps or [])
    parts.extend(record.keywords or [])
    return " \n ".join(parts).lower()


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _collect_verbs() -> set[str]:
    seen: set[str] = set()
    for vs in IMPERATIVE_VERBS.values():
        seen.update(v.lower() for v in vs)
    return seen


_ALL_VERBS: set[str] = _collect_verbs()
_ALL_UNITS: set[str] = {u.lower() for u in UNIT_TOKENS}


def score_procedural_density(record: VideoRecord) -> float:
    """Return a [0, 1] density: normalized (verbs + units + quantities) per 100 tokens."""
    text = _text_of(record)
    tokens = _tokenize(text)
    if not tokens:
        return 0.0

    verb_hits = sum(1 for t in tokens if t in _ALL_VERBS)
    unit_hits = sum(1 for t in tokens if t in _ALL_UNITS)
    quantity_hits = len(_QUANTITY_RE.findall(text))
    step_bonus = min(1.0, len(record.recipe_steps or []) / 8.0)

    per_100 = 100.0 * (verb_hits + unit_hits + quantity_hits) / max(len(tokens), 1)
    density = min(1.0, per_100 / 20.0)
    return 0.7 * density + 0.3 * step_bonus


def score_record_v2(record: VideoRecord) -> float:
    """Procedural-boost profile.

    Additive-with-clamp so v2 >= v1 for every record: procedural density
    can only *promote* candidates, never demote them. This keeps the
    baseline Pareto-safe on any fixture — an ablation over the seed
    baseline can never regress on `mean_quality`.
    """
    base = v1.score_record(record)
    proc = score_procedural_density(record)
    bonus = 0.25 * proc * (1.0 - base)
    return max(0.0, min(1.0, base + bonus))


PROFILES: dict[str, Callable[[VideoRecord], float]] = {
    "v1": v1.score_record,
    "v2_procedural": score_record_v2,
}


def score_records_with_profile(records: Iterable[VideoRecord], profile: str) -> list[VideoRecord]:
    if profile not in PROFILES:
        raise KeyError(f"unknown scorer profile: {profile}; known={sorted(PROFILES)}")
    fn = PROFILES[profile]
    return [r.with_quality(fn(r)) for r in records]
