"""Tests for `specint.yield_estimator`."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from specint.records import License, Provenance, VideoRecord
from specint.yield_estimator import UPSTREAM_CENSOR_THRESHOLD, estimate, to_rows


def _rec(id_: str, license_: License) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=id_.split(":", 1)[0],
        source_native_id=id_.split(":", 1)[1],
        url=f"https://example.test/{id_.replace(':', '/')}",
        title="x",
        license=license_,
        provenance=Provenance(extractor="test", fetched_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )


def test_estimate_empty_records_is_zero_rate():
    e = estimate("wikimedia", upstream_total_hits=0, records=[])
    assert e.records_parsed == 0
    assert e.license_clean_rate == 0.0
    assert e.projected_daily_records == 0
    assert e.censored is False


def test_estimate_half_clean_rate():
    recs = [
        _rec("wikimedia:1", License.CC_BY),
        _rec("wikimedia:2", License.UNKNOWN),
    ]
    e = estimate("wikimedia", upstream_total_hits=200, records=recs, batch_size=50)
    assert e.records_parsed == 2
    assert e.records_license_clean == 1
    assert abs(e.license_clean_rate - 0.5) < 1e-9
    assert e.censored is False
    # projected_daily_records = 2000 * 50 * 0.5 = 50_000
    assert e.projected_daily_records == 50_000


def test_censored_above_threshold():
    e = estimate("archive_org", upstream_total_hits=UPSTREAM_CENSOR_THRESHOLD + 1, records=[])
    assert e.censored is True


def test_serialization_roundtrip_is_json_safe():
    e = estimate("peertube", upstream_total_hits=10, records=[_rec("peertube:1", License.CC0)])
    payload = json.dumps(to_rows([e]), sort_keys=True)
    reloaded = json.loads(payload)
    assert reloaded[0]["source"] == "peertube"
    assert reloaded[0]["records_license_clean"] == 1
