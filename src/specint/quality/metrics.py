"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only*
so we can rank a backlog of millions of candidates before deciding
which to actually download.

Components:
  - license_clean : 1 if license is redistributable, else 0.
  - duration      : see :class:`DurationProfile`. Default profile is
                    ``short_form`` (peaks at 5 min) for backwards
                    compatibility with ``reports/baseline-2026-06-20.json``.
                    The ``long_form`` profile peaks around 10 min and
                    decays out to ~45 min per W4 in
                    ``docs/plan-2026-08-25.md``.
  - resolution    : >=720p ramps from 0 to 1.
  - text_density  : combined length of title + description + recipe_steps.
  - has_steps     : 1 if recipe_steps non-empty (procedural supervision).

Adding a component:
  1. Implement a new ``_score_*`` function returning a float in [0, 1].
  2. Add it to :data:`WEIGHTS` with a documented rationale.
  3. Update tests in ``tests/test_quality.py`` with the new lower/upper
     bounds.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from enum import Enum

from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.15,
    "has_steps": 0.15,
}


class DurationProfile(str, Enum):  # - keep classic str+Enum for CLI arg parity with License
    """Domain-calibrated duration curve.

    ``short_form``: legacy, peaks at 300s (single-recipe montage).
    ``long_form`` : log-normal-shaped curve peaking around 600s
    (10-minute procedural), gently decaying out to ~45 minutes. This
    matches the CaptainCook4D / ProMQA / VideoAuteur long-form
    horizons called out in the 2026-08-25 adversarial plan (W4).
    """

    SHORT_FORM = "short_form"
    LONG_FORM = "long_form"


DEFAULT_DURATION_PROFILE = DurationProfile.SHORT_FORM


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration_short_form(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))


def _score_duration_long_form(record: VideoRecord) -> float:
    """Log-normal-shaped curve peaking around 600s.

    ``sigma`` widens the plateau so a 3-minute and a 20-minute recipe
    still both score above 0.5. Records with unknown duration keep
    getting 0 so we never over-promote uncalibrated items.
    """
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    peak = 600.0
    sigma = 0.9
    log_ratio = math.log(d / peak)
    return math.exp(-((log_ratio) ** 2) / (2 * sigma * sigma))


_DURATION_PROFILES = {
    DurationProfile.SHORT_FORM: _score_duration_short_form,
    DurationProfile.LONG_FORM: _score_duration_long_form,
}


def _score_duration(record: VideoRecord, profile: DurationProfile) -> float:
    return _DURATION_PROFILES[profile](record)


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


def score_record(
    record: VideoRecord,
    duration_profile: DurationProfile = DEFAULT_DURATION_PROFILE,
) -> float:
    total_weight = sum(WEIGHTS.values())
    components = {
        "license_clean": _score_license(record),
        "duration": _score_duration(record, duration_profile),
        "resolution": _score_resolution(record),
        "text_density": _score_text_density(record),
        "has_steps": _score_has_steps(record),
    }
    raw = sum(WEIGHTS[name] * value for name, value in components.items())
    return raw / total_weight if total_weight else 0.0


def score_records(
    records: Iterable[VideoRecord],
    duration_profile: DurationProfile = DEFAULT_DURATION_PROFILE,
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, duration_profile)) for r in records]
