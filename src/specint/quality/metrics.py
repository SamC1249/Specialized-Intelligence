"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot for a
                          single recipe), penalizes very short and very long.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description + recipe_steps.
  - has_steps           : 1 if recipe_steps non-empty (procedural supervision).
  - procedural_density  : imperative verbs + numeric quantities + temporal
                          expressions per 100 tokens; capped at 1.0.
                          Isolates "action per token" from marketing prose.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.12,
    "resolution": 0.18,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_density": 0.20,
}

_IMPERATIVE_VERBS: frozenset[str] = frozenset(
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
        "chop",
        "combine",
        "cook",
        "cool",
        "cover",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "drizzle",
        "flip",
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
        "mash",
        "melt",
        "mince",
        "mix",
        "pat",
        "peel",
        "place",
        "pour",
        "preheat",
        "press",
        "prepare",
        "puree",
        "reduce",
        "remove",
        "return",
        "rinse",
        "roast",
        "roll",
        "rub",
        "saute",
        "sauté",
        "scoop",
        "sear",
        "season",
        "serve",
        "set",
        "shake",
        "sift",
        "simmer",
        "slice",
        "spoon",
        "spread",
        "sprinkle",
        "stir",
        "strain",
        "taste",
        "temper",
        "top",
        "toss",
        "transfer",
        "turn",
        "wait",
        "whip",
        "whisk",
    }
)

_TIME_UNITS = frozenset(
    {
        "s",
        "sec",
        "secs",
        "second",
        "seconds",
        "m",
        "min",
        "mins",
        "minute",
        "minutes",
        "h",
        "hr",
        "hrs",
        "hour",
        "hours",
    }
)
_QUANTITY_UNITS = frozenset(
    {
        "g",
        "kg",
        "mg",
        "ml",
        "l",
        "oz",
        "lb",
        "lbs",
        "tsp",
        "tbsp",
        "tbs",
        "cup",
        "cups",
        "pinch",
        "clove",
        "cloves",
        "slice",
        "slices",
        "piece",
        "pieces",
        "%",
    }
)

_TOKEN_RE = re.compile(r"[\w%°]+", flags=re.UNICODE)
_NUMBER_RE = re.compile(r"^\d+(?:[./]\d+)?$")


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0  # 5 minutes
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))  # decays out to ~1 hour


def _score_resolution(record: VideoRecord) -> float:
    h = record.height
    if h is None or h <= 0:
        return 0.0
    if h >= 1080:
        return 1.0
    if h >= 720:
        return 0.8
    if h >= 480:
        return 0.5
    return 0.2


def _score_text_density(record: VideoRecord) -> float:
    chars = len(record.title) + len(record.description)
    seen: set[str] = set()
    for step in record.recipe_steps:
        key = step.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        chars += len(step)
    if chars <= 0:
        return 0.0
    target = 800.0
    return min(1.0, chars / target)


def _score_has_steps(record: VideoRecord) -> float:
    return 1.0 if record.recipe_steps else 0.0


def _iter_tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(text)]


def procedural_density_raw(text: str) -> float:
    """Return imperative+quantity+time hits per 100 tokens, capped at 1.0."""
    tokens = _iter_tokens(text)
    if not tokens:
        return 0.0
    hits = 0
    for i, tok in enumerate(tokens):
        if tok in _IMPERATIVE_VERBS:
            hits += 1
            continue
        if _NUMBER_RE.match(tok):
            hits += 1
            if i + 1 < len(tokens) and tokens[i + 1] in (_TIME_UNITS | _QUANTITY_UNITS):
                hits += 1
            continue
        if tok in _TIME_UNITS or tok in _QUANTITY_UNITS:
            hits += 1
    ratio = hits / max(1, len(tokens))
    return min(1.0, ratio * 8.0)


def _score_procedural_density(record: VideoRecord) -> float:
    combined = " ".join([record.title, record.description, *record.recipe_steps])
    seen: set[str] = set()
    dedup_steps: list[str] = []
    for step in record.recipe_steps:
        key = step.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            dedup_steps.append(step)
    if len(dedup_steps) < len(record.recipe_steps):
        combined = " ".join([record.title, record.description, *dedup_steps])
    return procedural_density_raw(combined)


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
}


def score_record(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[name] * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight if total_weight else 0.0


def score_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record(r)) for r in records]
