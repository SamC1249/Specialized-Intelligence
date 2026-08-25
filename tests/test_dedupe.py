"""Offline tests for the metadata-only dedup pass."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedupe import canonical_url, dedupe_summary, jaccard, merge_records, title_shingles
from specint.records import License, Provenance, VideoRecord


def _rec(id_: str, url: str, title: str, source: str = "wikimedia", **kw) -> VideoRecord:
    base = dict(
        id=f"{source}:{id_}",
        source=source,
        source_native_id=id_,
        url=url,
        title=title,
        description="",
        provenance=Provenance(
            extractor="t",
            extractor_git="abc1234",
            fetched_at=datetime.now(UTC),
            query="q",
            raw_sha256="0" * 64,
        ),
    )
    base.update(kw)
    return VideoRecord(**base)


def test_canonical_url_strips_tracking_and_normalizes_youtube():
    assert (
        canonical_url("HTTPS://www.YouTube.com/watch?v=abc123&utm_source=x&feature=share")
        == "https://www.youtube.com/watch?v=abc123"
    )
    assert canonical_url("https://youtu.be/abc123") == "https://www.youtube.com/watch?v=abc123"
    assert canonical_url("https://example.test/foo/") == "https://example.test/foo"


def test_title_shingles_and_jaccard():
    a = title_shingles("Garlic butter pasta recipe", k=5)
    b = title_shingles("garlic-butter pasta recipe!!!", k=5)
    assert jaccard(a, b) > 0.9
    c = title_shingles("beef wellington plating tutorial", k=5)
    assert jaccard(a, c) < 0.1


def test_tier1_canonical_url_merges_youtube_variants():
    r1 = _rec("1", "https://youtu.be/xyz", "Cooking demo", source="wikimedia")
    r2 = _rec(
        "2", "https://www.youtube.com/watch?v=xyz&utm_source=x", "Cooking demo", source="peertube"
    )
    merged = merge_records([r1, r2])
    assert len(merged) == 1
    assert "merged=" in merged[0].provenance.query


def test_tier2_title_shingles_merges_near_duplicates_across_sources():
    r1 = _rec(
        "1",
        "https://a.test/p1",
        "Classic Garlic Butter Pasta",
        source="wikimedia",
        license=License.CC_BY,
    )
    r2 = _rec(
        "2",
        "https://b.test/p2",
        "Classic garlic-butter pasta!",
        source="archive_org",
        license=License.CC0,
    )
    merged = merge_records([r1, r2], threshold=0.7)
    assert len(merged) == 1


def test_same_source_never_merged_at_tier_2():
    r1 = _rec("1", "https://a.test/p1", "Homemade tomato sauce", source="wikimedia")
    r2 = _rec("2", "https://a.test/p2", "Homemade tomato sauce", source="wikimedia")
    merged = merge_records([r1, r2], threshold=0.5)
    assert len(merged) == 2


def test_dedupe_summary_counts_are_consistent():
    r1 = _rec("1", "https://youtu.be/abc", "foo", source="a")
    r2 = _rec("2", "https://www.youtube.com/watch?v=abc", "foo", source="b")
    r3 = _rec("3", "https://c.test/x", "totally unrelated", source="c")
    out, stats = dedupe_summary([r1, r2, r3])
    assert stats["n_input"] == 3
    assert stats["n_output"] == len(out) == 2
    assert stats["n_dupes_collapsed"] == 1
    assert stats["n_pairs_by_canonical_url"] == 1
