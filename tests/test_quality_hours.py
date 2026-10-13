"""Tests for the duration-weighted `quality_hours` metric."""

from __future__ import annotations

import pytest

from specint.compare.harness import aggregate
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(duration_s: float, quality: float, lic: License = License.CC_BY) -> VideoRecord:
    return VideoRecord(
        id=f"test:{duration_s}:{quality}",
        source="test",
        source_native_id=f"{duration_s}-{quality}",
        url="https://example.test/a",
        title="t",
        license=lic,
        duration_s=duration_s,
        provenance=Provenance(extractor="test", query="q"),
    ).with_quality(quality)


def test_quality_hours_is_duration_weighted_mean() -> None:
    records = [_rec(600, 0.8), _rec(60, 0.8)]  # 10 min + 1 min at same quality
    row = aggregate("test", ["q"], records)
    # (600*0.8 + 60*0.8) / 3600 == 0.1466...
    assert row.quality_hours == pytest.approx((600 * 0.8 + 60 * 0.8) / 3600.0)
    # Same mean quality, very different quality_hours.
    assert row.mean_quality == pytest.approx(0.8)


def test_quality_hours_zero_on_empty_input() -> None:
    row = aggregate("test", ["q"], [])
    assert row.quality_hours == 0.0


def test_quality_hours_ignores_missing_duration() -> None:
    records = [
        _rec(0.0, 0.9),  # no duration contribution
        _rec(360, 0.5),  # 6 min * 0.5 = 180 s = 0.05 h
    ]
    row = aggregate("test", ["q"], records)
    assert row.quality_hours == pytest.approx(360 * 0.5 / 3600.0)
