"""Unit tests for cross-source deduplication."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.dedup import (
    deduplicate,
    group_duplicates,
    normalize_title,
    pick_canonical,
)
from specint.records import License, Provenance, VideoRecord


def _rec(**over) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Some Video",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(over)
    return VideoRecord(**base)


def test_normalize_title_strips_punctuation_and_casefolds():
    assert normalize_title("Hello, WORLD!") == "hello world"
    assert normalize_title("  Spaghetti   Carbonara  ") == "spaghetti carbonara"
    assert normalize_title("") == ""


def test_group_duplicates_merges_same_title_and_duration():
    a = _rec(
        id="wikimedia:1",
        source="wikimedia",
        source_native_id="1",
        title="Homemade Sourdough Demo",
        duration_s=300.0,
        author="Jane",
    )
    b = _rec(
        id="archive_org:1",
        source="archive_org",
        source_native_id="1",
        title="Homemade Sourdough Demo!",
        duration_s=302.0,
        author="Jane",
    )
    groups = group_duplicates([a, b])
    assert len(groups) == 1
    assert {r.source for r in groups[0]} == {"wikimedia", "archive_org"}


def test_group_duplicates_does_not_merge_when_duration_differs():
    a = _rec(id="a:1", source="a", title="Pasta", duration_s=60.0)
    b = _rec(id="b:1", source="b", title="Pasta", duration_s=600.0)
    groups = group_duplicates([a, b])
    assert len(groups) == 2


def test_group_duplicates_is_idempotent():
    recs = [
        _rec(id="a:1", source="a", title="X", duration_s=100.0),
        _rec(id="b:1", source="b", title="X", duration_s=100.0),
        _rec(id="c:1", source="c", title="Y", duration_s=50.0),
    ]
    once = group_duplicates(recs)
    twice = group_duplicates([g[0] for g in once])
    assert [r.id for g in twice for r in g] == [g[0].id for g in once]


def test_pick_canonical_prefers_higher_quality_then_license():
    a = _rec(id="a:1", source="a", quality_score=0.4, license=License.CC0)
    b = _rec(id="b:1", source="b", quality_score=0.8, license=License.UNKNOWN)
    c = _rec(id="c:1", source="c", quality_score=0.8, license=License.CC_BY)
    picked = pick_canonical([a, b, c])
    assert picked.id == "c:1"


def test_deduplicate_returns_one_per_group():
    a = _rec(id="a:1", source="a", title="X", duration_s=100.0, quality_score=0.6)
    b = _rec(id="b:1", source="b", title="X", duration_s=100.0, quality_score=0.9)
    c = _rec(id="c:1", source="c", title="Y", duration_s=50.0, quality_score=0.3)
    result = deduplicate([a, b, c])
    ids = {r.id for r in result}
    assert ids == {"b:1", "c:1"}


def test_empty_title_records_are_never_merged():
    a = _rec(id="a:1", source="a", title="", duration_s=100.0)
    b = _rec(id="b:1", source="b", title="", duration_s=100.0)
    groups = group_duplicates([a, b])
    assert len(groups) == 2
