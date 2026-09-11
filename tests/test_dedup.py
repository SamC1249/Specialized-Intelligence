"""Tests for the cross-source deduplicator.

These are pure-function tests: build synthetic `VideoRecord`s in-memory
and assert deterministic dedup behaviour. No fixtures, no network.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedup import (
    author_slug,
    dedupe,
    duration_bucket,
    fingerprint,
    normalize_title,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str,
    source: str,
    title: str,
    duration: float | None,
    author: str | None,
    quality: float = 0.5,
    license_: License = License.CC_BY,
) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=source,
        source_native_id=id_.split(":", 1)[-1],
        url=f"https://example.test/{id_}",
        title=title,
        description="",
        duration_s=duration,
        author=author,
        license=license_,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    ).with_quality(quality)


def test_normalize_title_strips_case_punct_diacritics():
    assert normalize_title("Sauté the Onions!") == "saute the onions"
    assert normalize_title("  Multi   space  ") == "multi space"
    assert normalize_title("") == ""


def test_normalize_title_strips_wiki_prefix_and_video_extension():
    assert normalize_title("File:NASA Kitchen Physics 101.webm") == "nasa kitchen physics 101"
    assert normalize_title("Some Video.mp4") == "some video"


def test_duration_bucket_is_stable_within_5s():
    assert duration_bucket(302.0) == duration_bucket(304.9)
    assert duration_bucket(302.0) != duration_bucket(305.0)
    assert duration_bucket(None) == -1
    assert duration_bucket(-1) == -1


def test_fingerprint_matches_across_sources_for_same_asset():
    a = _rec("wikimedia:1", "wikimedia", "NASA Kitchen Physics 101", 302.0, "NASA Educational")
    b = _rec("archive_org:x", "archive_org", "NASA Kitchen Physics 101", 304.0, "NASA Educational")
    assert fingerprint(a) == fingerprint(b)


def test_dedupe_keeps_higher_quality_across_sources():
    a = _rec(
        "wikimedia:1",
        "wikimedia",
        "NASA Kitchen Physics 101",
        302.0,
        "NASA Educational",
        quality=0.9,
    )
    b = _rec(
        "archive_org:x",
        "archive_org",
        "NASA Kitchen Physics 101",
        304.0,
        "NASA Educational",
        quality=0.4,
    )
    c = _rec("peertube:foo", "peertube", "Unique demo", 120.0, "Chef Foo", quality=0.5)
    kept, report = dedupe([a, b, c])
    kept_ids = {r.id for r in kept}
    assert kept_ids == {"wikimedia:1", "peertube:foo"}
    assert report.n_in == 3
    assert report.n_out == 2
    assert report.n_dropped == 1
    assert report.duplicate_rate == 1 / 3
    assert len(report.groups) == 1
    grp = report.groups[0]
    assert grp.kept_id == "wikimedia:1"
    assert grp.dropped_ids == ["archive_org:x"]


def test_dedupe_does_not_collide_when_authors_differ():
    a = _rec("wikimedia:1", "wikimedia", "Chocolate cake", 300.0, "Teacher A")
    b = _rec("wikimedia:2", "wikimedia", "Chocolate cake", 300.0, "Teacher B")
    kept, report = dedupe([a, b])
    assert len(kept) == 2
    assert report.n_dropped == 0


def test_dedupe_leaves_empty_fingerprint_records_alone():
    a = _rec("s:1", "s", "", None, None)
    b = _rec("s:2", "s", "", None, None)
    kept, report = dedupe([a, b])
    assert len(kept) == 2
    assert report.n_dropped == 0


def test_author_slug_normalizes_like_title():
    assert author_slug("NASA Éducational") == "nasa educational"
    assert author_slug(None) == ""


def test_dedupe_is_deterministic_on_tied_quality():
    a = _rec("wikimedia:1", "wikimedia", "same", 300.0, "same", quality=0.5)
    b = _rec("archive_org:1", "archive_org", "same", 300.0, "same", quality=0.5)
    kept_ids_first = sorted(r.id for r in dedupe([a, b])[0])
    kept_ids_second = sorted(r.id for r in dedupe([b, a])[0])
    assert kept_ids_first == kept_ids_second
