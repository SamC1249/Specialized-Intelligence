"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot for a
                          single recipe), penalizes very short and very
                          long.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description +
                          recipe_steps.
  - procedural_density  : count of imperative-verb starts across title +
                          description + recipe_steps, saturating around
                          8 steps. Supersedes the older binary
                          `has_steps` signal, which is retained at a low
                          weight for backwards comparability.
  - has_steps           : 1 if recipe_steps non-empty (procedural
                          supervision). Kept at a small weight so
                          historical reports remain comparable.
  - language_match      : soft match against `SourceQuery.language`. See
                          `specint.quality.language.matches_target`.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `DEFAULT_WEIGHTS` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.

Backwards compatibility: the default weight vector is exposed as
`DEFAULT_WEIGHTS` and re-exported as `WEIGHTS` so any older caller /
report generator keeps working.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Mapping

from specint.quality.language import matches_target
from specint.records import VideoRecord

DEFAULT_WEIGHTS: dict[str, float] = {
    "license_clean": 0.32,
    "duration": 0.13,
    "resolution": 0.18,
    "text_density": 0.10,
    "procedural_density": 0.14,
    "has_steps": 0.05,
    "language_match": 0.08,
}

WEIGHTS: dict[str, float] = dict(DEFAULT_WEIGHTS)


IMPERATIVE_HINTS: frozenset[str] = frozenset(
    {
        "add", "bake", "beat", "blend", "boil", "brown", "brush", "chop",
        "combine", "cook", "cool", "cover", "cut", "dice", "drain",
        "drizzle", "dust", "fold", "fry", "garnish", "glaze", "grate",
        "grease", "grill", "heat", "knead", "layer", "let", "marinate",
        "melt", "mince", "mix", "peel", "place", "poach", "pour",
        "preheat", "prepare", "press", "reduce", "remove", "rinse",
        "roast", "roll", "saute", "sauté", "sear", "season", "serve",
        "shred", "sift", "simmer", "slice", "sprinkle", "steam", "stir",
        "strain", "toast", "toss", "transfer", "turn", "whisk", "wrap",
    }
)


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))


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


def _count_imperatives(text: str) -> int:
    if not text:
        return 0
    hits = 0
    for raw in text.replace("\n", ".").split("."):
        token = raw.strip().split(" ")[0].strip(",;:!?()[]\"'").lower()
        if token in IMPERATIVE_HINTS:
            hits += 1
    return hits


def _score_procedural_density(record: VideoRecord) -> float:
    hits = _count_imperatives(record.title)
    hits += _count_imperatives(record.description)
    for step in record.recipe_steps:
        hits += max(1, _count_imperatives(step))
    saturation = 8.0
    return min(1.0, hits / saturation)


def _score_language_match(record: VideoRecord, target: str | None) -> float:
    if record.language and target and record.language == target:
        return 1.0
    combined = record.title
    if record.description:
        combined = combined + " " + record.description
    return matches_target(combined, target)


_ComponentFn = Callable[[VideoRecord], float]

_COMPONENTS: dict[str, _ComponentFn] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "procedural_density": _score_procedural_density,
    "has_steps": _score_has_steps,
}


def component_scores(
    record: VideoRecord, target_language: str | None = None
) -> dict[str, float]:
    scores = {name: fn(record) for name, fn in _COMPONENTS.items()}
    scores["language_match"] = _score_language_match(record, target_language)
    return scores


def score_record(
    record: VideoRecord,
    weights: Mapping[str, float] | None = None,
    target_language: str | None = None,
) -> float:
    w = dict(weights) if weights is not None else DEFAULT_WEIGHTS
    scores = component_scores(record, target_language=target_language)
    total_weight = sum(w.get(k, 0.0) for k in scores)
    if total_weight <= 0:
        return 0.0
    raw = sum(w.get(k, 0.0) * v for k, v in scores.items())
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    weights: Mapping[str, float] | None = None,
    target_language: str | None = None,
) -> list[VideoRecord]:
    return [
        r.with_quality(score_record(r, weights=weights, target_language=target_language))
        for r in records
    ]
