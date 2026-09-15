from datetime import UTC, datetime

from specint.quality.dedup import (
    canonical_title,
    canonical_url,
    content_fingerprint,
    deduplicate,
    normalise_author,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    source: str,
    native_id: str,
    *,
    title: str,
    url: str,
    media_url: str | None = None,
    author: str | None = None,
    duration_s: float | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=f"{source}:{native_id}",
        source=source,
        source_native_id=native_id,
        url=url,
        media_url=media_url,
        title=title,
        author=author,
        duration_s=duration_s,
        license=License.CC0,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


def test_canonical_title_strips_punct_and_folds_ascii():
    assert canonical_title("  Café  au--Lait!  ") == "cafe au lait"
    assert canonical_title("Chef's Knife 101") == "chef s knife 101"


def test_canonical_url_removes_scheme_and_trailing_slash():
    assert canonical_url("https://Example.com/watch/1/") == "example.com/watch/1"
    assert canonical_url(None) is None


def test_normalise_author_lowercase_and_fold():
    assert normalise_author("Jáne  Cook") == "jane cook"


def test_content_fingerprint_requires_title_and_duration():
    r = _rec("a", "1", title="x", url="https://e.test/1")
    assert content_fingerprint(r) is None
    r2 = _rec("a", "1", title="x", url="https://e.test/1", duration_s=42.0)
    assert content_fingerprint(r2) is not None


def test_deduplicate_collapses_media_url_mirrors():
    a = _rec(
        "wikimedia",
        "1",
        title="Knife skills demo",
        url="https://commons.wikimedia.org/wiki/File:Knife_skills.webm",
        media_url="https://cdn.example/knife.webm",
        duration_s=45.0,
    )
    b = _rec(
        "archive_org",
        "2",
        title="Knife Skills Demo",
        url="https://archive.org/details/knife",
        media_url="https://cdn.example/knife.webm",
        duration_s=45.0,
    )
    kept, report = deduplicate([a, b])
    assert len(kept) == 1
    assert kept[0].source == "wikimedia"
    assert report.n_collisions == 1
    assert report.collisions_by_key["media_url"] == 1


def test_deduplicate_fingerprint_matches_across_sources():
    a = _rec(
        "wikimedia",
        "1",
        title="Cooking pasta carbonara",
        url="https://commons.wikimedia.org/wiki/File:Pasta.webm",
        author="Jane Cook",
        duration_s=312.0,
    )
    b = _rec(
        "archive_org",
        "9",
        title="  Cooking Pasta CARBONARA! ",
        url="https://archive.org/details/pasta",
        author="Jane  Cook",
        duration_s=315.0,
    )
    kept, report = deduplicate([a, b])
    assert len(kept) == 1
    assert report.collision_matrix["archive_org::wikimedia"] == 1
    assert report.collisions_by_key["fingerprint"] == 1


def test_deduplicate_keeps_unknown_duration_records_separate():
    a = _rec("wikimedia", "1", title="soup", url="https://a.test/1")
    b = _rec("archive_org", "2", title="soup", url="https://b.test/2")
    kept, report = deduplicate([a, b])
    assert len(kept) == 2
    assert report.n_collisions == 0


def test_deduplicate_url_collision_does_not_count_media():
    a = _rec("wikimedia", "1", title="a", url="https://x.test/1", duration_s=10.0)
    b = _rec("archive_org", "2", title="b", url="https://X.test/1/", duration_s=99.0)
    kept, report = deduplicate([a, b])
    assert len(kept) == 1
    assert report.collisions_by_key["url"] == 1


def test_dedup_report_totals_are_consistent():
    a = _rec("wikimedia", "1", title="x", url="https://a.test/1", duration_s=10.0)
    b = _rec("wikimedia", "1", title="x", url="https://a.test/1", duration_s=10.0)
    c = _rec("archive_org", "3", title="z", url="https://c.test/3")
    kept, report = deduplicate([a, b, c])
    assert report.n_input == 3
    assert report.n_unique == len(kept)
    assert report.n_input == report.n_unique + report.n_collisions
    assert sum(report.per_source_unique.values()) == report.n_unique
