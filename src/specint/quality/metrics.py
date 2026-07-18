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
  - text_density        : combined length of title + description +
                          recipe_steps.
  - has_steps           : 1 if recipe_steps non-empty (procedural
                          supervision).
  - procedural_density  : rewards records whose text carries dense,
                          state-changing action signal (imperative verbs,
                          time/temperature literals, discrete steps). See
                          `docs/artifacts/2025-worldprediction.md` for the
                          motivation.

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
    "resolution": 0.16,
    "text_density": 0.12,
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
        "chop",
        "combine",
        "cook",
        "cover",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "fold",
        "fry",
        "garnish",
        "grate",
        "grill",
        "heat",
        "knead",
        "marinate",
        "melt",
        "mince",
        "mix",
        "peel",
        "pour",
        "preheat",
        "reduce",
        "roast",
        "saute",
        "sauté",
        "sear",
        "season",
        "serve",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stir",
        "toast",
        "toss",
        "whisk",
    }
)

_TIME_TEMP_RE = re.compile(
    r"""
    \b(
        \d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)\b
        | \d+\s*(?:°|deg(?:rees)?)\s*(?:c|f|celsius|fahrenheit)?\b
        | \d{2,3}\s*(?:c|f)\b
    )
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)
_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


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
    chars += sum(len(s) for s in record.recipe_steps)
    if chars <= 0:
        return 0.0
    target = 800.0
    return min(1.0, chars / target)


def _score_has_steps(record: VideoRecord) -> float:
    return 1.0 if record.recipe_steps else 0.0


def _score_procedural_density(record: VideoRecord) -> float:
    """Reward records whose metadata implies dense procedural content.

    Three sub-signals, each capped at 1.0 and averaged with equal weight:
      - verb_hits    : imperative-verb tokens matched anywhere in
                       title + description + step text.
      - time_temp    : count of "N minutes / 350 F / 180 °C"-style
                       literals — canonical world-model state cues.
      - step_count   : number of `recipe_steps` entries (procedural
                       decomposition already done by upstream).
    """
    haystack_parts = [record.title, record.description, " ".join(record.recipe_steps)]
    haystack = " ".join(p for p in haystack_parts if p)
    if not haystack.strip():
        return 0.0

    tokens = [t.lower() for t in _TOKEN_RE.findall(haystack)]
    verb_hits = sum(1 for t in tokens if t in _IMPERATIVE_VERBS)
    verb_score = min(1.0, verb_hits / 6.0)

    time_temp_hits = len(_TIME_TEMP_RE.findall(haystack))
    time_temp_score = min(1.0, time_temp_hits / 3.0)

    step_score = min(1.0, len(record.recipe_steps) / 8.0)

    return (verb_score + time_temp_score + step_score) / 3.0


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
