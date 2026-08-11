"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Components:
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot for a
                          single recipe), penalizes very short and very
                          long clips.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description +
                          recipe_steps.
  - has_steps           : 1 if recipe_steps non-empty (procedural
                          supervision).
  - language_confidence : 2026-08-11 addition — cheap metadata-only
                          language-detection confidence. Not in the
                          default `WEIGHTS`; kept available for
                          ablation experiments (see
                          `specint.compare.ablation`).

The default `WEIGHTS` vector is the *baseline*. Any PR that changes it
must justify the change with a fresh `python -m specint ablate` report.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from specint.quality.language import language_confidence
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


def _score_language_confidence(record: VideoRecord) -> float:
    return language_confidence(record)


COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "language_confidence": _score_language_confidence,
}


def score_record(record: VideoRecord, weights: Mapping[str, float] | None = None) -> float:
    w = weights if weights is not None else WEIGHTS
    total_weight = sum(w.values())
    if total_weight <= 0:
        return 0.0
    raw = 0.0
    for name, weight in w.items():
        fn = COMPONENTS.get(name)
        if fn is None:
            continue
        raw += weight * fn(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    weights: Mapping[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, weights=weights)) for r in records]
