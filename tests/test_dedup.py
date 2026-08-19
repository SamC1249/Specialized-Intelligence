from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.quality.dedup import (
    JACCARD_THRESHOLD,
    canonicalize_url,
    dedupe,
    jaccard,
    normalize_title,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    rid: str,
    url: str,
    title: str,
    *,
    source: str = "wikimedia",
    author: str | None = None,
    duration: float | None = None,
    lic: License = License.CC_BY,
    media: str | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=rid,
        source=source,
        source_native_id=rid,
        url=url,
        media_url=media,
        title=title,
        description="",
        duration_s=duration,
        license=lic,
        author=author,
        provenance=Provenance(extractor="test", fetched_at=datetime.now(UTC), query="q"),
    )


def test_canonicalize_url_strips_www_and_query_and_thumb():
    a = canonicalize_url("https://www.commons.wikimedia.org/wiki/File:Foo.webm?variant=1#part")
    b = canonicalize_url("http://commons.wikimedia.org/wiki/File:Foo.webm")
    assert a == b


def test_canonicalize_url_collapses_archive_download_to_details():
    a = canonicalize_url("https://archive.org/download/my_item/my_item.mp4")
    b = canonicalize_url("https://archive.org/details/my_item")
    assert a == b


def test_jaccard_bounds_and_identity():
    assert jaccard(set(), set()) == 1.0
    assert jaccard({"a"}, set()) == 0.0
    assert 0.0 < jaccard({"a", "b"}, {"a", "c"}) < 1.0


def test_normalize_title_lowercases_and_tokenizes():
    assert normalize_title("Cooking PASTA — Carbonara!") == "cooking pasta carbonara"


def test_dedupe_collapses_same_url():
    a = _rec("wikimedia:1", "https://commons.wikimedia.org/wiki/File:Foo.webm", "Foo cooking")
    b = _rec(
        "archive_org:2",
        "https://commons.wikimedia.org/wiki/File:Foo.webm?v=1",
        "Foo cooking mirror",
    )
    report = dedupe([a, b])
    assert report.n_unique == 1
    assert report.pairs_by_signal["url"] == 1


def test_dedupe_collapses_similar_titles_with_matching_duration():
    a = _rec("s1:1", "https://a.example/one", "Homemade carbonara pasta recipe", duration=310)
    b = _rec("s2:1", "https://b.example/two", "Homemade carbonara pasta recipe!", duration=311)
    report = dedupe([a, b])
    assert report.n_unique == 1
    assert report.pairs_by_signal["title_jaccard"] == 1


def test_dedupe_keeps_distinct_records():
    a = _rec("wikimedia:1", "https://commons.wikimedia.org/wiki/File:Foo.webm", "Cooking pasta")
    b = _rec(
        "archive_org:2", "https://archive.org/details/bar", "Baking bread with sourdough starter"
    )
    report = dedupe([a, b])
    assert report.n_unique == 2
    assert not report.duplicates


def test_dedupe_prefers_license_clean_representative():
    a = _rec(
        "wikimedia:1",
        "https://x.example/1",
        "Same clip about pasta",
        author="Same",
        duration=100.0,
        lic=License.UNKNOWN,
    )
    b = _rec(
        "archive_org:2",
        "https://y.example/2",
        "Same clip about pasta.",
        author="Same",
        duration=100.0,
        lic=License.CC_BY,
    )
    report = dedupe([a, b])
    assert report.n_unique == 1
    representative = report.unique[0]
    assert representative.license is License.CC_BY


def test_jaccard_threshold_is_reasonable():
    assert 0.5 < JACCARD_THRESHOLD <= 1.0


def test_dedupe_empty_input():
    report = dedupe([])
    assert report.n_unique == 0
    assert report.duplicates == []
    assert report.clusters == []


@pytest.mark.parametrize(
    "url_a,url_b",
    [
        (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Foo.webm/800px-Foo.webm.jpg",
            "https://upload.wikimedia.org/wikipedia/commons/a/a1/Foo.webm/800px-Foo.webm.jpg",
        ),
    ],
)
def test_canonicalize_url_wikimedia_thumb_matches_original(url_a: str, url_b: str):
    assert canonicalize_url(url_a) == canonicalize_url(url_b)
