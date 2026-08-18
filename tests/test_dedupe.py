"""Cross-source dedupe.

The same underlying video appears on multiple sources — most commonly
Blender Foundation shorts on both PeerTube (`video.blender.org`) and
Wikimedia Commons. `dedupe_records` should collapse them into a single
record and prefer the record with the higher-tier licence.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specint.compare import dedupe_records
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    id: str,
    source: str,
    media_url: str | None,
    license: License,
    quality: float | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=id,
        source=source,
        source_native_id=id.split(":", 1)[-1],
        url=f"https://example.test/{source}/{id}",
        media_url=media_url,
        title="Big Buck Bunny short",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
        license=license,
        quality_score=quality,
    )


def test_dedupe_by_media_url_prefers_higher_tier_license():
    a = _rec(
        id="peertube:bbb",
        source="peertube",
        media_url="https://cdn.example.test/BBB.mp4",
        license=License.CC_BY_SA,
        quality=0.6,
    )
    b = _rec(
        id="wikimedia:BBB",
        source="wikimedia",
        media_url="https://cdn.example.test/BBB.mp4/",  # trailing slash, still same
        license=License.CC0,
        quality=0.55,
    )
    out = dedupe_records([a, b])
    assert len(out) == 1
    assert out[0].license is License.CC0


def test_dedupe_records_without_media_url_are_passthrough():
    a = _rec(id="cc:1", source="common_crawl", media_url=None, license=License.UNKNOWN)
    b = _rec(id="cc:2", source="common_crawl", media_url=None, license=License.UNKNOWN)
    out = dedupe_records([a, b])
    assert {r.id for r in out} == {"cc:1", "cc:2"}


def test_dedupe_url_normalization_covers_scheme_case_and_trailing_slash():
    a = _rec(
        id="a:1",
        source="a",
        media_url="HTTPS://Cdn.EXAMPLE.test/x.mp4",
        license=License.CC_BY,
        quality=0.4,
    )
    b = _rec(
        id="b:1",
        source="b",
        media_url="https://cdn.example.test/x.mp4",
        license=License.CC_BY,
        quality=0.9,
    )
    out = dedupe_records([a, b])
    assert len(out) == 1
    assert out[0].quality_score == 0.9
