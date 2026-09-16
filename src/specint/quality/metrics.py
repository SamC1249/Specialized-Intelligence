"""Metadata-only quality scoring.

Each scoring component returns a value in `[0, 1]`; the final score is a
weighted sum, also in `[0, 1]`. Scoring is deliberately *metadata-only*
so we can rank a backlog of millions of candidates before deciding
which to actually download.

Components (current):
  - license_clean : 1 if license is redistributable, else 0.
  - duration      : peaks at 5 minutes (procedural sweet spot for a
                    single recipe), penalizes very short and very long.
  - resolution    : >=720p ramps from 0 to 1.
  - text_density  : combined length of title + description +
                    recipe_steps.
  - has_steps     : 1 if recipe_steps non-empty (procedural
                    supervision signal).
  - relevance     : multilingual cooking-relevance from
                    `quality.relevance.score_relevance` (used by the
                    `cooking` profile; not part of the frozen
                    `baseline` profile).

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Register it in `_COMPONENTS` below.
  3. Add it (with a documented rationale) to a profile in
     `quality/profiles.py`.
  4. Update tests in `tests/test_quality.py` with the new lower/upper
     bounds.

Backwards compat:
  `WEIGHTS` is the frozen "baseline" profile and stays exported so
  existing imports and reports keep working. `score_record` /
  `score_records` continue to default to the baseline profile.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from specint.quality.profiles import BASELINE, get_profile
from specint.quality.relevance import score_relevance
from specint.records import VideoRecord

WEIGHTS: dict[str, float] = dict(BASELINE)


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


def _score_relevance(record: VideoRecord) -> float:
    return score_relevance(record).score


_COMPONENTS: dict[str, Callable[[VideoRecord], float]] = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "relevance": _score_relevance,
}


def _resolve_profile(profile: str | Mapping[str, float] | None) -> Mapping[str, float]:
    if profile is None:
        return BASELINE
    if isinstance(profile, str):
        return get_profile(profile)
    return profile


def score_record(
    record: VideoRecord,
    profile: str | Mapping[str, float] | None = None,
) -> float:
    weights = _resolve_profile(profile)
    total_weight = sum(weights.values())
    if not total_weight:
        return 0.0
    raw = 0.0
    for name, weight in weights.items():
        fn = _COMPONENTS.get(name)
        if fn is None:
            raise KeyError(f"unknown scoring component: {name!r}")
        raw += weight * fn(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord],
    profile: str | Mapping[str, float] | None = None,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, profile=profile)) for r in records]
