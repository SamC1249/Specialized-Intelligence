"""Tests for cross-source deduplication."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedup import (
    deduplicate,
    duplicate_rate,
    is_duplicate,
    unique_duration_s,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    id_: str,
    source: str,
    title: str,
    duration_s: float | None = 300.0,
    author: str | None = None,
    quality: float | None = None,
    license_: License = License.CC_BY,
) -> VideoRecord:
    prov = Provenance(
        extractor="tests.test_dedup",
        fetched_at=datetime(2026, 7, 11, tzinfo=UTC),
        query="terms=cooking;max=25;lang=",
    )
    return VideoRecord(
        id=id_,
        source=source,
        source_native_id=id_.split(":", 1)[-1],
        url="https://example.test/video",
        title=title,
        duration_s=duration_s,
        author=author,
        license=license_,
        provenance=prov,
        quality_score=quality,
    )


def test_identical_titles_and_duration_are_duplicates():
    a = _rec(id_="wikimedia:1", source="wikimedia", title="Boiling Eggs", duration_s=120.0)
    b = _rec(id_="archive_org:x", source="archive_org", title="Boiling Eggs", duration_s=121.0)
    assert is_duplicate(a, b)


def test_different_titles_are_not_duplicates_even_if_duration_matches():
    a = _rec(id_="a:1", source="s1", title="Boiling Eggs", duration_s=120.0)
    b = _rec(id_="b:1", source="s2", title="Roasting Beef", duration_s=120.0)
    assert not is_duplicate(a, b)


def test_missing_duration_falls_back_to_author_equality():
    a = _rec(id_="a:1", source="s1", title="How to Chop Garlic", duration_s=None, author="Chef Sam")
    b = _rec(id_="b:1", source="s2", title="how to chop garlic", duration_s=None, author="chef sam")
    assert is_duplicate(a, b)


def test_missing_duration_and_missing_author_never_duplicates():
    a = _rec(id_="a:1", source="s1", title="Same Title", duration_s=None, author=None)
    b = _rec(id_="b:1", source="s2", title="Same Title", duration_s=None, author=None)
    assert not is_duplicate(a, b)


def test_deduplicate_keeps_highest_quality_winner():
    a = _rec(id_="wikimedia:1", source="wikimedia", title="Pasta Recipe", quality=0.9)
    b = _rec(id_="archive_org:1", source="archive_org", title="Pasta Recipe", quality=0.5)
    winners = deduplicate([a, b])
    assert len(winners) == 1
    assert winners[0].id == "wikimedia:1"


def test_deduplicate_transitive_group():
    a = _rec(id_="s1:1", source="s1", title="Boiling Eggs", quality=0.4)
    b = _rec(id_="s2:1", source="s2", title="Boiling Eggs", quality=0.7)
    c = _rec(id_="s3:1", source="s3", title="Boiling Eggs", quality=0.5)
    winners = deduplicate([a, b, c])
    assert len(winners) == 1
    assert winners[0].id == "s2:1"


def test_deduplicate_preserves_distinct_records():
    a = _rec(id_="s1:1", source="s1", title="Roasting Beef", quality=0.4)
    b = _rec(id_="s2:1", source="s2", title="Baking Bread", quality=0.7)
    winners = deduplicate([a, b])
    assert len(winners) == 2


def test_duplicate_rate_and_unique_duration():
    a = _rec(id_="s1:1", source="s1", title="Boiling Eggs", duration_s=300.0)
    b = _rec(id_="s2:1", source="s2", title="Boiling Eggs", duration_s=301.0)
    c = _rec(id_="s3:1", source="s3", title="Baking Bread", duration_s=180.0)
    rate = duplicate_rate([a, b, c])
    assert 0.3 < rate < 0.4
    assert unique_duration_s([a, b, c]) == 480.0 or unique_duration_s([a, b, c]) == 481.0


def test_empty_input_is_stable():
    assert deduplicate([]) == []
    assert duplicate_rate([]) == 0.0
    assert unique_duration_s([]) == 0.0
