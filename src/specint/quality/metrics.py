"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean      : 1 if license is redistributable, else 0.
  - duration           : peaks at 5 minutes (procedural sweet spot for a
                         single recipe), penalizes very short and very long.
  - resolution         : >=720p ramps from 0 to 1.
  - text_density       : combined length of title + description + recipe_steps.
  - procedural_density : graded cooking-specific supervision signal that
                         rewards (a) number of enumerated recipe steps,
                         (b) count of cooking-verb mentions in text, and
                         (c) presence of measurement/time phrases.
                         Replaces the previous binary `has_steps` lever;
                         score saturates smoothly so a single step with
                         no verbs does not dominate a well-annotated clip.

Design intent: this score is a *ranker*, not a classifier. Two records
with the same score are not asserted equivalent; a score of 0.6 only
promises "scanned better on cheap metadata than a 0.3". New components
must be documented, bounded, and attached to a benchmark delta before
their weight is tuned.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.quality.language import detect_language
from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.10,
    "procedural_density": 0.20,
}

COOKING_VERBS: frozenset[str] = frozenset(
    {
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "chill",
        "chop",
        "crush",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "fold",
        "fry",
        "garnish",
        "glaze",
        "grate",
        "grill",
        "knead",
        "marinate",
        "melt",
        "mince",
        "mix",
        "pan-fry",
        "poach",
        "preheat",
        "proof",
        "puree",
        "reduce",
        "rest",
        "roast",
        "saute",
        "sauté",
        "scald",
        "sear",
        "season",
        "shred",
        "simmer",
        "slice",
        "steam",
        "steep",
        "stew",
        "stir",
        "strain",
        "temper",
        "toast",
        "toss",
        "whip",
        "whisk",
        "zest",
    }
)
MEASUREMENT_RE = re.compile(
    r"\b("
    r"\d+(?:\.\d+)?\s*(?:g|kg|mg|ml|l|oz|lb|lbs|tsp|tbsp|cup|cups|quart|quarts|pint|pints|"
    r"°f|°c|degrees?|f|c|minute|minutes|min|hour|hours|hr|hrs|second|seconds|sec)"
    r")\b",
    re.IGNORECASE,
)


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


_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]*")


def _text_corpus(record: VideoRecord) -> str:
    parts = [record.title, record.description, *record.recipe_steps]
    return " ".join(p for p in parts if p)


def _count_cooking_verbs(text: str) -> int:
    if not text:
        return 0
    tokens = (m.group(0).lower() for m in _WORD_RE.finditer(text))
    return sum(1 for t in tokens if t in COOKING_VERBS)


def _count_measurements(text: str) -> int:
    if not text:
        return 0
    return len(MEASUREMENT_RE.findall(text))


def _score_procedural_density(record: VideoRecord) -> float:
    """Graded replacement for the previous binary `has_steps` component.

    Three sub-signals, each in [0, 1], averaged:
      - steps_score : saturating at 8 explicit recipe_steps.
      - verbs_score : saturating at 10 cooking-verb mentions.
      - measure_score : saturating at 5 measurement phrases.
    """
    text = _text_corpus(record)
    steps_score = min(1.0, len(record.recipe_steps) / 8.0)
    verbs_score = min(1.0, _count_cooking_verbs(text) / 10.0)
    measure_score = min(1.0, _count_measurements(text) / 5.0)
    return (steps_score + verbs_score + measure_score) / 3.0


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "procedural_density": _score_procedural_density,
}


def score_record(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[name] * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight if total_weight else 0.0


def enrich_language(record: VideoRecord) -> VideoRecord:
    """If the record has no language tag, infer one from title+description."""
    if record.language:
        return record
    inferred = detect_language(f"{record.title} {record.description}".strip())
    if not inferred:
        return record
    return record.model_copy(update={"language": inferred})


def score_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    out: list[VideoRecord] = []
    for r in records:
        r2 = enrich_language(r)
        out.append(r2.with_quality(score_record(r2)))
    return out
