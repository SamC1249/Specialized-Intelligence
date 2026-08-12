"""Tests for cross-source deduplication."""

from __future__ import annotations

from specint.dedupe import dedupe, fingerprint, group_by_fingerprint, overlap
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = {
        "id": "s:x",
        "source": "s",
        "source_native_id": "x",
        "url": "https://example.test/x",
        "title": "Garlic Butter Pasta",
        "author": "Open Kitchen",
        "duration_s": 492.0,
        "provenance": Provenance(extractor="t"),
        "license": License.CC_BY,
    }
    base.update(overrides)
    return VideoRecord(**base)


def test_fingerprint_stable_across_case_and_punctuation():
    a = _rec(title="Garlic Butter Pasta!")
    b = _rec(title="garlic  butter  pasta")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_differs_when_author_differs():
    a = _rec(author="Open Kitchen")
    b = _rec(author="Home Baker")
    assert fingerprint(a) != fingerprint(b)


def test_fingerprint_ascii_folds_unicode():
    a = _rec(title="Tortilla Española")
    b = _rec(title="Tortilla Espanola")
    assert fingerprint(a) == fingerprint(b)


def test_dedupe_keeps_highest_quality():
    a = _rec(id="a", source="a", source_native_id="a").with_quality(0.3)
    b = _rec(id="b", source="b", source_native_id="b").with_quality(0.9)
    out = dedupe([a, b])
    assert len(out) == 1
    assert out[0].id == "b"


def test_overlap_reports_shared_fingerprints_only():
    x = _rec(id="x", source="wikimedia", source_native_id="x")
    y = _rec(id="y", source="peertube", source_native_id="y")  # same fingerprint as x
    z = _rec(
        id="z",
        source="archive_org",
        source_native_id="z",
        title="Sourdough Bread",
        author="Home Baker",
        duration_s=1325.0,
    )
    by_source = {"wikimedia": [x], "peertube": [y], "archive_org": [z]}
    o = overlap(by_source)
    assert o == {"peertube__wikimedia": 1}


def test_group_by_fingerprint_collects_duplicates():
    a = _rec(id="a", source="a")
    b = _rec(id="b", source="b")
    c = _rec(id="c", source="c", title="Different Recipe", duration_s=120.0)
    grouped = group_by_fingerprint([a, b, c])
    assert len(grouped) == 2
    assert sorted(len(v) for v in grouped.values()) == [1, 2]
