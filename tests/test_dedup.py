"""Cross-source dedup tests."""

from __future__ import annotations

from datetime import datetime

from specint.dedup import DedupStats, dedup, fingerprint
from specint.records import License, Provenance, VideoRecord


def _r(
    source: str,
    id_: str,
    title: str,
    duration: float | None,
    license_: License = License.CC0,
    quality: float = 0.5,
) -> VideoRecord:
    r = VideoRecord(
        id=f"{source}:{id_}",
        source=source,
        source_native_id=id_,
        url=f"https://example.test/{source}/{id_}",
        title=title,
        duration_s=duration,
        license=license_,
        provenance=Provenance(extractor="test", fetched_at=datetime.fromtimestamp(0)),
    )
    return r.with_quality(quality)


def test_fingerprint_is_language_insensitive_to_casing_and_punct() -> None:
    a = _r("wikimedia", "1", "Cooking Pasta Carbonara!", 300.0)
    b = _r("archive_org", "2", "cooking pasta carbonara", 302.0)
    assert fingerprint(a) == fingerprint(b)


def test_dedup_keeps_highest_quality() -> None:
    a = _r("wikimedia", "1", "Pasta", 300.0, quality=0.4)
    b = _r("archive_org", "2", "pasta", 301.0, quality=0.9)
    kept, stats = dedup([a, b])
    assert len(kept) == 1
    assert kept[0].source == "archive_org"
    assert isinstance(stats, DedupStats)
    assert stats.input_count == 2
    assert stats.output_count == 1
    assert stats.rate == 0.5


def test_dedup_prefers_redistributable_license_on_tie() -> None:
    a = _r("peertube", "1", "Soup", 180.0, license_=License.UNKNOWN, quality=0.5)
    b = _r("wikimedia", "2", "Soup", 182.0, license_=License.CC_BY, quality=0.5)
    kept, _ = dedup([a, b])
    assert len(kept) == 1
    assert kept[0].license is License.CC_BY


def test_dedup_passes_through_untitled_records() -> None:
    a = _r("wikimedia", "a", "", None)
    b = _r("wikimedia", "b", "", None)
    kept, stats = dedup([a, b])
    assert stats.output_count == 2
    assert {r.id for r in kept} == {"wikimedia:a", "wikimedia:b"}


def test_dedup_rate_on_empty_is_zero() -> None:
    kept, stats = dedup([])
    assert kept == []
    assert stats.rate == 0.0
