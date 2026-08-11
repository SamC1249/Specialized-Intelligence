from datetime import UTC, datetime

from specint.compare.dedup import dedup_key, dedupe
from specint.records import License, Provenance, VideoRecord


def _rec(
    source: str,
    native_id: str,
    title: str,
    duration_s: float | None = None,
    license: License = License.UNKNOWN,
    quality: float | None = None,
) -> VideoRecord:
    rec = VideoRecord(
        id=f"{source}:{native_id}",
        source=source,
        source_native_id=native_id,
        url=f"https://example.test/{source}/{native_id}",
        title=title,
        description="",
        duration_s=duration_s,
        license=license,
        provenance=Provenance(extractor=source, fetched_at=datetime.now(UTC), query=""),
    )
    if quality is not None:
        rec = rec.with_quality(quality)
    return rec


def test_dedup_key_normalizes_punctuation_and_case():
    k1 = dedup_key(_rec("a", "1", "Modern Chef Demonstration!", duration_s=270))
    k2 = dedup_key(_rec("b", "2", "modern-chef  demonstration ", duration_s=272))
    assert k1 == k2


def test_dedup_collapses_cross_source_duplicates_and_prefers_license_clean():
    ao = _rec("archive_org", "1", "Modern Chef Demonstration", 270.0, License.UNKNOWN, 0.4)
    wm = _rec("wikimedia", "2", "Modern Chef Demonstration", 270.0, License.CC_BY, 0.6)
    other = _rec("peertube", "9", "Public-Domain Pancakes", 180.0, License.CC0, 0.5)

    result = dedupe([ao, wm, other])
    assert result.n_input == 3
    assert result.n_output == 2
    assert result.cross_source_duplicates == 1

    ids = {r.id for r in result.records}
    assert "wikimedia:2" in ids
    assert "archive_org:1" not in ids


def test_dedup_keeps_distinct_short_clips_with_different_titles():
    a = _rec("a", "1", "Pancakes", 180.0, License.CC0)
    b = _rec("b", "2", "Tortilla", 180.0, License.CC0)
    result = dedupe([a, b])
    assert result.n_output == 2
    assert result.cross_source_duplicates == 0
