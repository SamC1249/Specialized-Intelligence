"""Metadata-only quality scoring.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Profiles live in `specint.quality.profiles`. `v1` is the 2026-06-20
baseline and must not change — reports under `reports/baseline-*.json`
were produced with it. Newer profiles (`v2`, `v2_cooking`) add
cooking-relevance and language-known signals.

Adding a component:
  1. Register it in `profiles.COMPONENTS`.
  2. Add an entry in a new (or existing) profile whose weights sum to 1.
  3. Add unit-test bounds in `tests/test_quality.py`.
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.quality.profiles import PROFILES, score_with_profile
from specint.records import VideoRecord

DEFAULT_PROFILE = "v1"

# Backwards-compat alias retained so old callers of `metrics.WEIGHTS`
# continue to see the v1 weights.
WEIGHTS: dict[str, float] = dict(PROFILES[DEFAULT_PROFILE])


def score_record(record: VideoRecord, profile: str = DEFAULT_PROFILE) -> float:
    return score_with_profile(record, profile)


def score_records(
    records: Iterable[VideoRecord], profile: str = DEFAULT_PROFILE
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, profile)) for r in records]
