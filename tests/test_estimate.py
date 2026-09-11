"""Tests for the metadata-only yield estimator."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.estimate import estimate_source, estimate_yield
from specint.records import License, Provenance, VideoRecord


def _rec(id_: str, license_: License, duration_s: float | None) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=id_.split(":", 1)[0],
        source_native_id=id_.split(":", 1)[-1],
        url=f"https://example.test/{id_}",
        title=id_,
        duration_s=duration_s,
        license=license_,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


def test_estimate_source_counts_only_redistributable():
    recs = [
        _rec("wikimedia:1", License.CC_BY, 3600.0),
        _rec("wikimedia:2", License.RESTRICTED, 3600.0),
        _rec("wikimedia:3", License.UNKNOWN, 100.0),
    ]
    est = estimate_source("wikimedia", recs)
    assert est.n_records == 3
    assert est.n_license_clean == 1
    assert est.hours_license_clean == 1.0
    assert est.hours_projected == 1.0


def test_estimate_yield_aggregates_across_sources():
    by_source = {
        "wikimedia": [_rec("wikimedia:1", License.CC0, 1800.0)],
        "archive_org": [_rec("archive_org:1", License.PUBLIC_DOMAIN, 3600.0)],
        "peertube": [_rec("peertube:1", License.RESTRICTED, 3600.0)],
    }
    est = estimate_yield(by_source)
    assert est.total_hours_license_clean == 1.5
    slugs = {s.source for s in est.sources}
    assert slugs == {"wikimedia", "archive_org", "peertube"}


def test_projection_scales_linearly():
    by_source = {"s": [_rec("s:1", License.CC0, 3600.0)]}
    est = estimate_yield(by_source, projected_pages=10)
    assert est.total_hours_projected == 10.0
