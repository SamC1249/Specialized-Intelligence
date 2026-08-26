"""Ablation for the duration-profile refactor (W4)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.quality import DurationProfile, score_record
from specint.records import License, Provenance, VideoRecord


def _rec(duration_s: float | None) -> VideoRecord:
    return VideoRecord(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Long-form braise",
        description="",
        duration_s=duration_s,
        license=License.CC_BY,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


@pytest.mark.parametrize(
    ("duration_s", "profile", "min_expected"),
    [
        (300.0, DurationProfile.SHORT_FORM, 0.10),
        (900.0, DurationProfile.SHORT_FORM, 0.00),
        (600.0, DurationProfile.LONG_FORM, 0.12),
        (1800.0, DurationProfile.LONG_FORM, 0.05),
    ],
)
def test_profile_returns_reasonable_score(duration_s, profile, min_expected):
    got = score_record(_rec(duration_s), duration_profile=profile)
    assert got >= min_expected


def test_long_form_favours_10min_over_short_form():
    r10 = _rec(600.0)
    short = score_record(r10, duration_profile=DurationProfile.SHORT_FORM)
    long_ = score_record(r10, duration_profile=DurationProfile.LONG_FORM)
    assert long_ > short


def test_unknown_duration_scores_zero_component_either_way():
    r = _rec(None)
    a = score_record(r, duration_profile=DurationProfile.SHORT_FORM)
    b = score_record(r, duration_profile=DurationProfile.LONG_FORM)
    assert a == b  # duration contributes 0 to both, all other components equal
