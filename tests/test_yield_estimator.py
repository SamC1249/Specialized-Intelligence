from datetime import UTC, datetime

from specint.records import License, Provenance, VideoRecord
from specint.yield_estimator import estimate_yield, extract_listing_total


def _rec(license_=License.CC_BY, duration_s=300.0) -> VideoRecord:
    return VideoRecord(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="x",
        description="",
        license=license_,
        duration_s=duration_s,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


def test_extract_listing_total_wikimedia():
    raw = {"query": {"searchinfo": {"totalhits": 1234}}}
    assert extract_listing_total("wikimedia", raw) == 1234


def test_extract_listing_total_archive_org():
    raw = {"response": {"numFound": 42}}
    assert extract_listing_total("archive_org", raw) == 42


def test_extract_listing_total_peertube_and_youtube():
    assert extract_listing_total("peertube", {"total": 9}) == 9
    assert extract_listing_total("youtube", {"pageInfo": {"totalResults": 7}}) == 7


def test_extract_listing_total_missing_returns_none():
    assert extract_listing_total("wikimedia", {}) is None
    assert extract_listing_total("common_crawl", {"foo": 1}) is None
    assert extract_listing_total("unknown_source", {"total": 1}) is None


def test_estimate_yield_projects_upstream_total():
    sample = [_rec(License.CC_BY), _rec(License.CC_BY_SA), _rec(License.RESTRICTED)]
    est = estimate_yield("wikimedia", sample, upstream_total=3000)
    assert est.sample_size == 3
    assert est.license_clean_rate == 2 / 3
    assert est.est_records == 3000
    assert est.est_license_clean_records == 2000
    assert est.est_hours_landing_pages > 0.0
    assert est.est_hours_redistributable > 0.0


def test_estimate_yield_zero_redist_hours_for_youtube():
    sample = [_rec(License.CC_BY)]
    est = estimate_yield("youtube", sample, upstream_total=1000)
    assert est.est_hours_redistributable == 0.0
    assert est.est_hours_landing_pages > 0.0


def test_estimate_yield_empty_sample():
    est = estimate_yield("wikimedia", [], upstream_total=None)
    assert est.est_records == 0
    assert est.est_hours_landing_pages == 0.0
