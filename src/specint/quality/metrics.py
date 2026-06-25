"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components (current):
  - license_clean : 1 if license is redistributable, else 0.
  - duration      : peaks at 5 minutes (procedural sweet spot for a single
                    recipe), penalizes very short and very long.
  - resolution    : >=720p ramps from 0 to 1.
  - text_density  : combined length of title + description + recipe_steps.
  - has_steps     : 1 if recipe_steps non-empty (procedural supervision).

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.15,
    "has_steps": 0.15,
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


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
}


def score_record(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[name] * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight if total_weight else 0.0


def score_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record(r)) for r in records]
