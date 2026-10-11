from __future__ import annotations

from datetime import UTC, datetime

from specint.compare import observed_stats, project_hours_per_day
from specint.records import License, Provenance, VideoRecord


def _rec(duration: float | None, license: License) -> VideoRecord:
    return VideoRecord(
        id=f"test:{duration}-{license.value}",
        source="wikimedia",
        source_native_id=str(duration),
        url="https://example.test/x",
        media_url=None,
        title="x",
        description="",
        duration_s=duration,
        license=license,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query="q"),
    )


def test_project_hours_per_day_is_product():
    proj = project_hours_per_day(
        source="wikimedia",
        records_per_page=50,
        pages_per_day=480,
        mean_duration_s=180,
        license_clean_fraction=1.0,
    )
    assert proj.source == "wikimedia"
    assert proj.records_per_day == 24000.0
    assert proj.hours_per_day == 24000.0 * 180.0 / 3600.0 == 1200.0


def test_project_hours_per_day_clamps_fraction_and_negatives():
    proj = project_hours_per_day(
        source="s",
        records_per_page=-5,
        pages_per_day=10,
        mean_duration_s=10,
        license_clean_fraction=2.0,
    )
    assert proj.records_per_day == 0.0
    assert proj.hours_per_day == 0.0


def test_observed_stats_empty_input():
    assert observed_stats([]) == (0.0, 0.0)


def test_observed_stats_mixes_license_and_duration():
    records = [
        _rec(60, License.CC_BY),
        _rec(120, License.CC_BY_SA),
        _rec(None, License.UNKNOWN),
        _rec(600, License.RESTRICTED),
    ]
    mean, clean = observed_stats(records)
    assert mean == (60 + 120 + 600) / 3
    assert clean == 2 / 4


def test_yield_projection_as_dict_is_rounded_and_serialisable():
    proj = project_hours_per_day("s", 50, 480, 180, 1.0, notes="n")
    d = proj.as_dict()
    assert d == {"source": "s", "records_per_day": 24000.0, "hours_per_day": 1200.0, "notes": "n"}
