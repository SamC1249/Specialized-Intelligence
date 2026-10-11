from datetime import UTC, datetime

from specint.quality.dedupe import dedupe_records
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="x:1",
        source="x",
        source_native_id="1",
        url="https://example.test/1",
        title="Something",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_empty_input():
    out, stats = dedupe_records([])
    assert out == []
    assert stats.n_input == 0 and stats.n_output == 0


def test_primary_key_media_url_collapses_mirrors():
    a = _rec(
        id="wikimedia:7",
        source="wikimedia",
        media_url="https://cdn.example.test/video.mp4",
        license=License.CC_BY,
        quality_score=0.6,
    )
    b = _rec(
        id="archive_org:7",
        source="archive_org",
        media_url="https://cdn.example.test/video.mp4?utm=foo",
        license=License.CC0,
        quality_score=0.5,
    )
    out, stats = dedupe_records([a, b])
    assert len(out) == 1
    assert out[0].id == "wikimedia:7"  # higher quality wins
    assert stats.n_duplicates_dropped == 1
    assert stats.n_cross_source_pairs == 1


def test_soft_key_matches_on_title_author_duration_bucket():
    a = _rec(
        id="peertube:11",
        source="peertube",
        title="Weeknight Dal Tadka",
        author="Priya K.",
        duration_s=372.0,
    )
    b = _rec(
        id="common_crawl:11",
        source="common_crawl",
        title="  weeknight dal tadka ",
        author="Priya K",
        duration_s=378.0,
    )
    c = _rec(id="other:11", source="other", title="A totally different clip", duration_s=120.0)
    out, stats = dedupe_records([a, b, c])
    assert len(out) == 2
    assert stats.n_duplicates_dropped == 1
    assert stats.n_cross_source_pairs == 1


def test_license_clean_tiebreak_when_quality_equal():
    a = _rec(id="s1:1", source="s1", media_url="https://cdn.test/clip.mp4", license=License.UNKNOWN)
    b = _rec(id="s2:1", source="s2", media_url="https://cdn.test/clip.mp4", license=License.CC_BY)
    out, _ = dedupe_records([a, b])
    assert out[0].id == "s2:1"


def test_order_is_deterministic_on_shuffle():
    records = [
        _rec(id=f"s:{i}", source="s", title=f"Clip {i}", duration_s=100.0 + i)
        for i in range(5)
    ]
    out_a, _ = dedupe_records(records)
    out_b, _ = dedupe_records(list(reversed(records)))
    assert [r.id for r in out_a] == [r.id for r in out_b]
