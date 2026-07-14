"""Cross-source dedup tests."""

from __future__ import annotations

from specint.compare.dedup import dedupe_records, normalize_title, normalize_url
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str,
    url: str,
    title: str = "Pasta Carbonara",
    license: License = License.CC_BY_SA,
    duration_s: float | None = 300.0,
    author: str = "Author",
    source: str = "wikimedia",
    quality: float | None = 0.5,
) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=source,
        source_native_id=id_.split(":")[-1],
        url=url,
        title=title,
        license=license,
        duration_s=duration_s,
        author=author,
        provenance=Provenance(extractor="tests.dedup"),
        quality_score=quality,
    )


def test_normalize_url_strips_query_and_case():
    a = normalize_url("HTTPS://Example.com/foo/?a=1#top")
    b = normalize_url("https://example.com/foo")
    assert a == b


def test_normalize_title_collapses_punctuation():
    assert normalize_title("Pasta - Carbonara!") == "pasta carbonara"
    assert normalize_title("Pasta  -  Carbonara") == "pasta carbonara"


def test_dedup_by_url():
    records = [
        _rec("wikimedia:1", "https://commons.wikimedia.org/wiki/File:X.webm"),
        _rec(
            "archive_org:1",
            "https://commons.wikimedia.org/wiki/File:X.webm",
            source="archive_org",
            quality=0.7,
        ),
    ]
    unique, dropped = dedupe_records(records)
    assert dropped == 1
    assert len(unique) == 1


def test_dedup_by_title_and_duration_bucket():
    records = [
        _rec(
            "wikimedia:1",
            "https://commons.wikimedia.org/wiki/File:pasta_carbonara.webm",
            duration_s=298.0,
        ),
        _rec(
            "archive_org:2",
            "https://archive.org/details/pasta-carbonara",
            source="archive_org",
            duration_s=302.0,
        ),
    ]
    unique, dropped = dedupe_records(records)
    assert dropped == 1
    assert len(unique) == 1


def test_dedup_prefers_license_clean_then_quality():
    a = _rec("a:1", "https://a.example/x", license=License.UNKNOWN, quality=0.9)
    b = _rec("b:1", "https://a.example/x", license=License.CC_BY, quality=0.4)
    unique, dropped = dedupe_records([a, b])
    assert dropped == 1
    assert unique[0].id == "b:1"


def test_dedup_leaves_distinct_records():
    records = [
        _rec("wikimedia:1", "https://commons.wikimedia.org/pasta.webm", title="Pasta"),
        _rec(
            "wikimedia:2",
            "https://commons.wikimedia.org/risotto.webm",
            title="Risotto Milanese",
        ),
    ]
    unique, dropped = dedupe_records(records)
    assert dropped == 0
    assert len(unique) == 2
