"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Two weight dicts live here:

- `WEIGHTS`         — the *committed* baseline. Weights only change after
                      a recorded A/B win.
- `WEIGHTS_EXPERIMENTAL` — the current challenger. Add procedural
                      signals here at non-zero weight, prove they win on
                      the fixture harness, then promote in a *separate*
                      PR.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1]
     (or `None` if metadata is absent).
  2. Register it in `_COMPONENTS`.
  3. Add it to `WEIGHTS_EXPERIMENTAL` (never `WEIGHTS`) with a rationale.
  4. Add tests in `tests/test_quality.py` with the new lower/upper bounds.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from specint.quality.procedural import (
    PROCEDURAL_COMPONENTS,
    score_aspect_ratio,
    score_audio_present,
    score_cooking_verbs,
    score_shot_density_from_metadata,
)
from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.15,
    "has_steps": 0.15,
}

WEIGHTS_EXPERIMENTAL: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.10,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.10,
    "aspect_ratio": 0.10,
    "audio_present": 0.05,
    "cooking_verbs": 0.15,
    "shot_density": 0.05,
}


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0  # 5 minutes
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


_ComponentFn = Callable[[VideoRecord], float | None]

_COMPONENTS: dict[str, _ComponentFn] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "aspect_ratio": score_aspect_ratio,
    "audio_present": score_audio_present,
    "cooking_verbs": score_cooking_verbs,
    "shot_density": score_shot_density_from_metadata,
}

assert set(PROCEDURAL_COMPONENTS).issubset(_COMPONENTS)


def score_record(record: VideoRecord, weights: Mapping[str, float] | None = None) -> float:
    """Weighted sum of registered components. Missing signals are dropped from
    both numerator and denominator so a record with no width/height isn't
    unfairly zeroed on `aspect_ratio`.
    """
    w = weights or WEIGHTS
    total_weight = 0.0
    total = 0.0
    for name, weight in w.items():
        fn = _COMPONENTS.get(name)
        if fn is None or weight == 0:
            continue
        value = fn(record)
        if value is None:
            continue
        total += float(weight) * float(value)
        total_weight += float(weight)
    return total / total_weight if total_weight else 0.0


def score_records(
    records: Iterable[VideoRecord],
    weights: Mapping[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, weights=weights)) for r in records]
