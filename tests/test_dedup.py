from __future__ import annotations

from datetime import UTC, datetime

from specint.dedup import deduplicate
from specint.records import Provenance, VideoRecord


def _rec(
    source: str,
    native: str,
    url: str,
    title: str,
    *,
    duration_s: float | None = None,
    quality: float | None = None,
) -> VideoRecord:
    prov = Provenance(extractor=source, fetched_at=datetime.now(UTC), query="")
    r = VideoRecord(
        id=f"{source}:{native}",
        source=source,
        source_native_id=native,
        url=url,
        title=title,
        duration_s=duration_s,
        provenance=prov,
    )
    if quality is not None:
        r = r.with_quality(quality)
    return r


def test_dedup_by_normalized_url():
    a = _rec("wikimedia", "1", "https://commons.wikimedia.org/wiki/File:X.webm", "X", quality=0.4)
    b = _rec(
        "archive_org",
        "2",
        "https://COMMONS.wikimedia.org/wiki/File:X.webm/",
        "X copy",
        quality=0.9,
    )
    result = deduplicate([a, b])
    assert len(result.kept) == 1
    assert result.kept[0].source == "archive_org"
    assert result.n_removed == 1


def test_dedup_by_title_and_duration_match():
    a = _rec(
        "peertube",
        "1",
        "https://framatube.org/videos/watch/abc",
        "Cooking Pasta Carbonara",
        duration_s=300.0,
        quality=0.7,
    )
    b = _rec(
        "wikimedia",
        "2",
        "https://commons.wikimedia.org/wiki/File:Cooking-pasta.webm",
        "cooking pasta carbonara",
        duration_s=301.0,
        quality=0.5,
    )
    result = deduplicate([a, b])
    assert len(result.kept) == 1
    assert result.kept[0].source == "peertube"


def test_dedup_keeps_records_with_distinct_titles_and_urls():
    a = _rec("peertube", "1", "https://framatube.org/videos/watch/a", "Recipe A", quality=0.7)
    b = _rec(
        "wikimedia", "2", "https://commons.wikimedia.org/wiki/File:B.webm", "Recipe B", quality=0.7
    )
    result = deduplicate([a, b])
    assert len(result.kept) == 2
    assert result.n_removed == 0


def test_dedup_preserves_query_string_disambiguators():
    a = _rec("youtube_cc", "1", "https://www.youtube.com/watch?v=aaa", "Video A", quality=0.7)
    b = _rec("youtube_cc", "2", "https://www.youtube.com/watch?v=bbb", "Video B", quality=0.7)
    result = deduplicate([a, b])
    assert len(result.kept) == 2


def test_dedup_strips_tracking_params_but_keeps_id_params():
    a = _rec(
        "youtube_cc",
        "1",
        "https://www.youtube.com/watch?v=aaa&utm_source=twitter",
        "Same",
        duration_s=100.0,
        quality=0.5,
    )
    b = _rec(
        "youtube_cc",
        "2",
        "https://www.youtube.com/watch?v=aaa",
        "Same",
        duration_s=100.0,
        quality=0.9,
    )
    result = deduplicate([a, b])
    assert len(result.kept) == 1
    assert result.kept[0].source_native_id == "2"


def test_dedup_is_deterministic_on_ties():
    a = _rec("archive_org", "1", "https://archive.org/details/x", "Same title", quality=0.5)
    b = _rec("peertube", "2", "https://framatube.org/videos/watch/x", "Same title", quality=0.5)
    r1 = deduplicate([a, b])
    r2 = deduplicate([b, a])
    assert [r.id for r in r1.kept] == [r.id for r in r2.kept]
