from __future__ import annotations

from datetime import UTC, datetime

from specint.compare import dedup_records, run_comparison
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(rid: str, **overrides) -> VideoRecord:
    base: dict = dict(
        id=rid,
        source=overrides.pop("source", "wikimedia"),
        source_native_id=overrides.pop("source_native_id", rid.split(":")[-1]),
        url=overrides.pop("url", f"https://example.test/{rid}"),
        title=overrides.pop("title", f"Video {rid}"),
        description=overrides.pop("description", ""),
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_within_source_dedup_counts_duplicates():
    a = _rec("wikimedia:1", license=License.CC_BY)
    a_dup = _rec("wikimedia:1", license=License.CC_BY)
    b = _rec("wikimedia:2", license=License.CC0)
    rows = run_comparison(
        SourceQuery(terms=["x"]),
        {"wikimedia": [a, a_dup, b]},
    )
    wiki = next(r for r in rows if r.source == "wikimedia")
    total = next(r for r in rows if r.source == "__total__")
    assert wiki.n_records == 2
    assert wiki.n_duplicates == 1
    assert total.n_duplicates == 1


def test_run_comparison_is_deterministic():
    records = [
        _rec("wikimedia:1", license=License.CC_BY, duration_s=100.0),
        _rec("archive_org:2", license=License.PUBLIC_DOMAIN, duration_s=200.0),
    ]
    by_source = {
        "wikimedia": [records[0]],
        "archive_org": [records[1]],
    }
    q = SourceQuery(terms=["cook"])
    a = run_comparison(q, by_source)
    b = run_comparison(q, by_source)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]


def test_cross_source_dedup_prefers_stronger_license():
    a = _rec(
        "archive_org:1",
        source="archive_org",
        url="https://archive.org/details/x",
        media_url="https://cdn.example.test/videos/x.mp4",
        title="Same Clip",
        author="Alice",
        duration_s=120.0,
        license=License.CC_BY,
    )
    b = _rec(
        "wikimedia:9",
        source="wikimedia",
        url="https://commons.wikimedia.org/wiki/File:X",
        media_url="https://cdn.example.test/videos/x.mp4",
        title="Same Clip",
        author="Alice",
        duration_s=120.0,
        license=License.CC0,
    )
    report = dedup_records([a, b])
    assert report.n_removed == 1
    assert len(report.records) == 1
    survivor = report.records[0]
    assert survivor.license is License.CC0


def test_cross_source_dedup_no_media_url_uses_title_author_duration():
    a = _rec(
        "peertube:1",
        source="peertube",
        media_url=None,
        title="Sourdough Bread Tutorial",
        author="baker",
        duration_s=310.0,
        license=License.CC_BY,
    )
    b = _rec(
        "peertube:2",
        source="peertube",
        media_url=None,
        title="Sourdough Bread Tutorial!",
        author="Baker",
        duration_s=315.0,
        license=License.CC_BY_SA,
    )
    report = dedup_records([a, b])
    assert report.n_removed == 1


def test_cross_source_dedup_leaves_distinct_records():
    a = _rec("peertube:1", title="Bread", author="one", duration_s=100.0)
    b = _rec("peertube:2", title="Cookies", author="two", duration_s=300.0)
    report = dedup_records([a, b])
    assert report.n_removed == 0
    assert len(report.records) == 2
