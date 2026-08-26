"""Tests for phase-1 metadata deduplication (W6)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.dedup import deduplicate, fingerprint, jaccard, title_shingles
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str, title: str, duration_s: float, author: str | None, *, q: float = 0.5
) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=id_.split(":", 1)[0],
        source_native_id=id_.split(":", 1)[1],
        url=f"https://example.test/{id_}",
        title=title,
        description="",
        duration_s=duration_s,
        author=author,
        license=License.CC_BY,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
        quality_score=q,
    )


def test_fingerprint_stable_across_case_and_punctuation():
    a = _rec("wikimedia:1", "Cooking Pasta Carbonara!", 312.0, "Jane Cook")
    b = _rec("archive_org:x", "cooking pasta carbonara", 312.4, "jane cook")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_distinguishes_different_duration():
    a = _rec("wikimedia:1", "Knife skills demo", 120.0, "Alice")
    b = _rec("archive_org:2", "Knife skills demo", 480.0, "Alice")
    assert fingerprint(a) != fingerprint(b)


def test_title_shingles_and_jaccard():
    a = _rec("s:1", "cooking pasta carbonara at home", 300.0, None)
    b = _rec("s:2", "cooking pasta carbonara at home HD", 300.0, None)
    sa = title_shingles(a)
    sb = title_shingles(b)
    assert jaccard(sa, sb) >= 0.5
    assert jaccard(sa, sa) == 1.0
    assert jaccard(frozenset(), frozenset()) == 1.0
    assert jaccard(sa, frozenset()) == 0.0


def test_deduplicate_keeps_highest_quality_survivor():
    a = _rec("wikimedia:1", "Cooking Pasta Carbonara", 312.0, "Jane Cook", q=0.9)
    b = _rec("archive_org:2", "cooking pasta carbonara", 312.4, "jane cook", q=0.4)
    c = _rec("peertube:3", "Knife skills demo", 60.0, "Alice", q=0.7)
    result = deduplicate([b, a, c])
    ids = {r.id for r in result.kept}
    assert ids == {"wikimedia:1", "peertube:3"}
    assert result.removed == 1


def test_deduplicate_deterministic_when_scores_tied():
    a = _rec("archive_org:1", "same title", 100.0, "X", q=0.5)
    b = _rec("wikimedia:1", "same title", 100.0, "X", q=0.5)
    r1 = deduplicate([a, b])
    r2 = deduplicate([b, a])
    assert [r.id for r in r1.kept] == [r.id for r in r2.kept]
    assert r1.removed == r2.removed == 1


@pytest.mark.parametrize("empty_input", [[], iter(())])
def test_deduplicate_empty(empty_input):
    r = deduplicate(empty_input)
    assert r.kept == []
    assert r.removed == 0
