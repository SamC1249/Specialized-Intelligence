from datetime import UTC, datetime

from specint.quality import dedupe
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="a:1",
        source="a",
        source_native_id="1",
        url="https://example.test/a/1",
        title="Cooking Pasta Carbonara",
        author="Jane Cook",
        duration_s=310.0,
        license=License.CC_BY_SA,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_dedupe_merges_same_title_author_across_sources():
    r1 = _rec(id="wikimedia:12", source="wikimedia", source_native_id="12")
    r2 = _rec(
        id="archive_org:X",
        source="archive_org",
        source_native_id="X",
        url="https://example.test/archive/X",
        duration_s=312.0,
    )
    canonical, report = dedupe([r1, r2])
    assert report.input_n == 2
    assert report.output_n == 1
    assert report.n_clusters_gt1 == 1
    assert len(canonical) == 1
    winner_sources = {c.sources for c in report.clusters}
    assert ("archive_org", "wikimedia") in winner_sources


def test_dedupe_keeps_distinct_titles_separate():
    r1 = _rec(id="a:1", title="Pasta Carbonara")
    r2 = _rec(id="b:1", source="b", source_native_id="1", title="Sourdough Bread")
    canonical, report = dedupe([r1, r2])
    assert report.output_n == 2
    assert report.n_clusters_gt1 == 0
    assert {r.id for r in canonical} == {"a:1", "b:1"}


def test_dedupe_requires_two_signals():
    same_title_only = _rec(id="a:1", title="Pancakes")
    other = _rec(
        id="b:1",
        source="b",
        source_native_id="1",
        title="Pancakes",
        author="Someone Else",
        duration_s=45.0,
    )
    _, report = dedupe([same_title_only, other])
    assert report.n_clusters_gt1 == 0


def test_dedupe_prefers_more_permissive_license():
    strong = _rec(
        id="cc0:1", source="cc0", source_native_id="1", license=License.CC0, duration_s=300.0
    )
    weaker = _rec(id="restricted:1", source="restricted", source_native_id="1")
    canonical, report = dedupe([strong, weaker])
    assert report.output_n == 1
    assert canonical[0].id == "cc0:1"


def test_empty_dedupe():
    canonical, report = dedupe([])
    assert canonical == []
    assert report.input_n == 0 and report.output_n == 0
    assert report.reduction == 0.0


def test_dedupe_by_media_url_hash_alone_is_two_signals():
    r1 = _rec(
        id="a:1",
        title="Different Title A",
        media_url="https://cdn.example/videos/xyz.mp4",
    )
    r2 = _rec(
        id="b:1",
        source="b",
        source_native_id="1",
        title="Different Title B",
        author="Other",
        duration_s=100.0,
        media_url="https://cdn.example/videos/xyz.mp4",
    )
    _, report = dedupe([r1, r2])
    assert report.n_clusters_gt1 == 1
