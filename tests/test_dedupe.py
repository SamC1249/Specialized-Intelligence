"""Tests for `specint.dedupe`."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedupe import cluster, dedupe, dedupe_stats
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str,
    title: str,
    duration: float | None,
    license_: License = License.UNKNOWN,
    quality: float | None = None,
):
    return VideoRecord(
        id=id_,
        source=id_.split(":", 1)[0],
        source_native_id=id_.split(":", 1)[1],
        url=f"https://example.test/{id_.replace(':', '/')}",
        title=title,
        description="",
        duration_s=duration,
        license=license_,
        quality_score=quality,
        provenance=Provenance(extractor="test", fetched_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )


def test_cluster_groups_cross_source_near_duplicates():
    records = [
        _rec("wikimedia:1", "Cooking pasta carbonara.webm", 312.4, License.CC_BY_SA),
        _rec("archive_org:1", "Cooking Pasta Carbonara", 310.0, License.UNKNOWN),
        _rec("peertube:1", "Open-Source Sourdough", 642.0, License.CC_BY_SA),
    ]
    clusters = cluster(records)
    biggest = max(clusters, key=lambda c: len(c.members))
    assert len(biggest.members) == 2
    sources = {m.source for m in biggest.members}
    assert sources == {"wikimedia", "archive_org"}


def test_dedupe_prefers_license_clean_winner():
    a = _rec("wikimedia:2", "Knife skills demo", 45.0, License.CC0)
    b = _rec("archive_org:2", "Knife skills demo", 45.0, License.UNKNOWN)
    survivors = dedupe([a, b])
    assert len(survivors) == 1
    assert survivors[0].license is License.CC0


def test_dedupe_tie_breaks_on_quality_then_duration_then_id():
    a = _rec("a:1", "Same", 60.0, License.CC_BY, quality=0.6)
    b = _rec("b:1", "Same", 60.0, License.CC_BY, quality=0.9)
    assert dedupe([a, b])[0].id == "b:1"


def test_empty_title_records_are_singletons():
    records = [_rec("x:1", "", 10.0), _rec("x:2", "", 10.0)]
    clusters = cluster(records)
    assert len(clusters) == 2


def test_dedupe_stats_counts_duplicates_removed():
    records = [
        _rec("wikimedia:1", "Cooking pasta carbonara.webm", 312.4, License.CC_BY_SA),
        _rec("archive_org:1", "Cooking Pasta Carbonara", 310.0, License.UNKNOWN),
        _rec("peertube:1", "Open-Source Sourdough", 642.0, License.CC_BY_SA),
    ]
    stats = dedupe_stats(records)
    assert stats["n_records"] == 3
    assert stats["n_clusters"] == 2
    assert stats["n_duplicates_removed"] == 1
    assert stats["n_license_clean_before"] == 2
    # The dedupe winner for the duplicate pair is CC-BY-SA; cleanness holds.
    assert stats["n_license_clean_after"] == 2
