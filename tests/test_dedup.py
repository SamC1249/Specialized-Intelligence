"""Cross-source dedup unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import DedupCluster, dedup_records, duration_bucket, normalize_title
from specint.records import License, Provenance, VideoRecord


def _rec(rid: str, source: str, title: str, duration: float | None, **overrides) -> VideoRecord:
    base = dict(
        id=rid,
        source=source,
        source_native_id=rid.split(":", 1)[-1],
        url=f"https://example.test/{rid.replace(':', '/')}",
        title=title,
        duration_s=duration,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_normalize_title_strips_case_diacritics_and_punctuation():
    assert normalize_title("Cooking, Part 1!") == "cooking part 1"
    assert normalize_title("Crème brûlée") == "creme brulee"
    assert normalize_title("") == ""


def test_duration_bucket_is_stable_and_none_becomes_minus_one():
    assert duration_bucket(0) == -1
    assert duration_bucket(None) == -1
    assert duration_bucket(29) == 0
    assert duration_bucket(30) == 1
    assert duration_bucket(120) == 4


def test_dedup_collapses_cross_source_duplicates_and_keeps_provenance():
    a = _rec(
        "wikimedia:1",
        "wikimedia",
        "Garlic Butter Pasta",
        300.0,
        license=License.CC_BY,
        quality_score=0.7,
    )
    b = _rec(
        "archive_org:1",
        "archive_org",
        "Garlic Butter Pasta!",
        305.0,  # same 30s bucket as a
        license=License.CC0,
        quality_score=0.6,
    )
    c = _rec("peertube:1", "peertube", "Sourdough basics", 900.0, license=License.CC_BY_SA)

    survivors, clusters = dedup_records([a, b, c])
    survivor_ids = {r.id for r in survivors}
    assert "peertube:1" in survivor_ids
    assert len(survivors) == 2  # a and b collapsed
    assert len(clusters) == 1
    cluster = clusters[0]
    assert isinstance(cluster, DedupCluster)
    # Survivor is the highest-quality record.
    assert cluster.survivor_id == "wikimedia:1"
    assert set(cluster.member_ids) == {"wikimedia:1", "archive_org:1"}
    assert set(cluster.member_sources) == {"wikimedia", "archive_org"}
    assert set(cluster.member_licenses) == {"CC-BY", "CC0"}


def test_dedup_refuses_to_over_merge_templated_titles_from_different_authors():
    parts = [
        _rec(f"src:{i}", "src", "Cooking, part 1", 60.0, author=f"Author-{i}") for i in range(5)
    ]
    survivors, clusters = dedup_records(parts, max_cluster_size=3)
    # Different authors → refuse to merge; survivors == inputs.
    assert len(survivors) == len(parts)
    assert clusters == []


def test_dedup_records_without_duration_and_empty_title_pass_through():
    orphan = _rec("src:1", "src", "", None)
    survivors, clusters = dedup_records([orphan])
    assert [r.id for r in survivors] == ["src:1"]
    assert clusters == []
