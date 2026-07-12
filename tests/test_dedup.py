"""Tests for metadata-only dedup (H2 in docs/plan-2026-07-12.md).

These tests exist to *pin* the current behavior. If you loosen the key
(e.g. drop duration from the tuple), the false-positive tests should
start failing; if you tighten it, the true-positive tests should start
failing. Both directions cost yield or precision — the tests force you
to argue for the trade in a PR.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.dedup import DedupKey, dedup_key, dedup_records
from specint.records import License, Provenance, VideoRecord

_PROV = Provenance(extractor="tests", fetched_at=datetime.now(UTC), query="q")


def _rec(
    id_: str,
    title: str,
    duration_s: float | None,
    author: str | None,
    source: str = "wikimedia",
    license_: License = License.CC_BY,
) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=source,
        source_native_id=id_.split(":", 1)[-1],
        url=f"https://example.org/{id_}",
        title=title,
        duration_s=duration_s,
        author=author,
        license=license_,
        provenance=_PROV,
    )


def test_dedup_key_shingles_are_stable_across_case_and_punctuation() -> None:
    a = dedup_key(_rec("a:1", "How to bake bread!", 300.0, "Chef Ada"))
    b = dedup_key(_rec("a:2", "how to BAKE bread", 300.0, "Chef Ada"))
    assert a.shingles == b.shingles
    assert a.is_duplicate_of(b)


def test_dedup_across_sources_same_content() -> None:
    r1 = _rec("wikimedia:1", "Blender Cooking Short", 240.0, "Blender Foundation", "wikimedia")
    r2 = _rec("archive_org:2", "Blender Cooking Short", 242.0, "Blender Foundation", "archive_org")
    r3 = _rec("peertube:3", "Blender Cooking Short", 240.0, "Blender Foundation", "peertube")
    deduped, clusters = dedup_records([r1, r2, r3])
    assert len(deduped) == 1
    assert clusters[0].size == 3
    assert deduped[0].id == "wikimedia:1"  # first-in wins


def test_dedup_does_not_collapse_different_authors() -> None:
    r1 = _rec("a:1", "Chocolate Cake", 300.0, "Ada")
    r2 = _rec("a:2", "Chocolate Cake", 300.0, "Bo")
    deduped, clusters = dedup_records([r1, r2])
    assert len(deduped) == 2
    assert all(c.size == 1 for c in clusters)


def test_dedup_does_not_collapse_different_durations() -> None:
    r1 = _rec("a:1", "Sourdough Basics", 300.0, "Ada")
    r2 = _rec("a:2", "Sourdough Basics", 900.0, "Ada")
    deduped, _ = dedup_records([r1, r2])
    assert len(deduped) == 2


def test_dedup_missing_duration_allows_merge_when_author_and_title_match() -> None:
    r1 = _rec("a:1", "Roast Chicken With Rosemary", 300.0, "Ada")
    r2 = _rec("a:2", "Roast Chicken With Rosemary", None, "Ada")
    deduped, clusters = dedup_records([r1, r2])
    assert len(deduped) == 1
    assert clusters[0].size == 2


def test_dedup_empty_titles_never_merge() -> None:
    """Two records both titled "" or filtered to no tokens must not
    collapse — an empty shingle set carries no evidence."""
    r1 = _rec("a:1", "", 300.0, "Ada")
    r2 = _rec("a:2", "recipe cooking video", 300.0, "Ada")  # all stop tokens
    deduped, _ = dedup_records([r1, r2])
    assert len(deduped) == 2


def test_dedup_empty_input() -> None:
    deduped, clusters = dedup_records([])
    assert deduped == []
    assert clusters == []


def test_dedup_key_type_semantics() -> None:
    """DedupKey exposes the primitives; the tests double as executable spec."""
    key = dedup_key(_rec("a:1", "The Best Bread Ever", 305.0, "Chef Ada"))
    assert isinstance(key, DedupKey)
    assert isinstance(key.shingles, frozenset)
    assert key.duration_bucket == 61  # round(305/5)
    assert key.author_slug == "chefada"
