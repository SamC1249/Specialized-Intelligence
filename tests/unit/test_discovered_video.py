"""Unit tests for the `DiscoveredVideo` record."""

from __future__ import annotations

from datetime import UTC, date, datetime

from specialized_intelligence.licenses import LicenseNorm
from specialized_intelligence.sources.base import DiscoveredVideo


def test_from_upstream_normalizes_license() -> None:
    rec = DiscoveredVideo.from_upstream(
        video_uri="youtube:abc123",
        source_id="yt_cc_api",
        title="How to dice an onion",
        license_tag="creativeCommon",
        discovered_at=datetime(2026, 6, 23, tzinfo=UTC),
        duration_s=312.4,
        upload_date=date(2024, 1, 1),
        channel_id="UCxxxx",
    )
    assert rec.license_norm is LicenseNorm.CC_BY
    assert rec.license_tag == "creativeCommon"
    assert rec.source_id == "yt_cc_api"


def test_unknown_license_yields_unknown_norm() -> None:
    rec = DiscoveredVideo.from_upstream(
        video_uri="weird:xyz",
        source_id="archive_org",
        title="Untitled",
        license_tag="all-rights-reserved",
        discovered_at=datetime(2026, 6, 23, tzinfo=UTC),
    )
    assert rec.license_norm is LicenseNorm.UNKNOWN
