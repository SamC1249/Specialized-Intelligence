"""Unit tests for cross-source deduplication."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.compare.dedup import (
    blocking_key,
    build_report,
    duration_bucket,
    find_clusters,
    normalize_title,
)
from specint.records import License, Provenance, VideoRecord


def _prov() -> Provenance:
    return Provenance(extractor="tests", fetched_at=datetime(2026, 9, 13, tzinfo=UTC))


def _rec(
    id_: str,
    source: str,
    title: str,
    duration_s: float | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=f"{source}:{id_}",
        source=source,
        source_native_id=id_,
        url=f"https://example.test/{source}/{id_}",
        title=title,
        duration_s=duration_s,
        license=License.CC_BY,
        provenance=_prov(),
    )


class TestNormalizeTitle:
    def test_strips_prefix_and_extension(self):
        assert normalize_title("File:Cooking Pasta Carbonara.webm") == "cooking pasta carbonara"

    def test_collapses_whitespace_and_punctuation(self):
        assert normalize_title("Cooking:   pasta — carbonara!") == "cooking pasta carbonara"

    def test_empty(self):
        assert normalize_title("") == ""


class TestDurationBucket:
    def test_none(self):
        assert duration_bucket(None) is None

    def test_rounds_to_30s(self):
        assert duration_bucket(312.4) == 300
        assert duration_bucket(298) == 300
        assert duration_bucket(316) == 330

    def test_negative_is_none(self):
        assert duration_bucket(-1) is None


class TestBlockingKey:
    def test_key(self):
        r = _rec("1", "peertube", "File:Cooking pasta.webm", duration_s=300)
        assert blocking_key(r) == ("cooking pasta", 300)


class TestFindClusters:
    def test_single_source_dup(self):
        recs = [
            _rec("1", "peertube", "Sourdough Bread", duration_s=600),
            _rec("2", "peertube", "SOURDOUGH bread!", duration_s=605),
        ]
        clusters = find_clusters(recs)
        assert len(clusters) == 1
        assert clusters[0].normalized_title == "sourdough bread"
        assert clusters[0].sources == ["peertube"]

    def test_cross_source_dup(self):
        recs = [
            _rec("1", "peertube", "Cooking Pasta Carbonara", duration_s=312),
            _rec("2", "wikimedia", "File:Cooking pasta carbonara.webm", duration_s=305),
        ]
        clusters = find_clusters(recs)
        assert len(clusters) == 1
        assert clusters[0].sources == ["peertube", "wikimedia"]

    def test_ignores_singletons(self):
        recs = [
            _rec("1", "peertube", "Unique thing", duration_s=100),
            _rec("2", "wikimedia", "Another unique thing", duration_s=100),
        ]
        assert find_clusters(recs) == []


class TestBuildReport:
    def test_counts(self):
        recs = [
            _rec("1", "peertube", "Cooking Pasta", duration_s=300),
            _rec("2", "wikimedia", "cooking pasta", duration_s=305),
            _rec("3", "archive_org", "distinct", duration_s=100),
        ]
        report = build_report(recs)
        assert report.n_records_in == 3
        assert report.n_duplicates_collapsed == 1
        assert report.n_records_out == 2
        assert report.n_cross_source_clusters == 1

    def test_empty(self):
        report = build_report([])
        assert report.n_records_in == 0
        assert report.n_duplicates_collapsed == 0
        assert report.clusters == []
