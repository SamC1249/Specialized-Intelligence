"""L1 (URL canonicalisation) + L2 (metadata bucket) dedup tests.

Covers the design in `docs/artifacts/2026-09-16-video-dedup.md`. Pure
functions only — no download, no framewise pHash. Those are deferred.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.quality.dedup import bucket_key, canonical_url, dedup
from specint.records import License, Provenance, VideoRecord


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "https://www.youtube.com/watch?v=abc123&utm_source=twitter",
            "https://www.youtube.com/watch?v=abc123",
        ),
        ("https://youtu.be/abc123?si=xyz", "https://www.youtube.com/watch?v=abc123"),
        ("http://Youtu.Be/abc123", "https://www.youtube.com/watch?v=abc123"),
        (
            "https://commons.wikimedia.org/wiki/Special:FilePath/Pasta.webm",
            "https://commons.wikimedia.org/wiki/File:Pasta.webm",
        ),
        (
            "https://commons.m.wikimedia.org/wiki/File:Pasta.webm",
            "https://commons.wikimedia.org/wiki/File:Pasta.webm",
        ),
        (
            "https://archive.org/details/foo?utm_medium=email&x=1",
            "https://archive.org/details/foo?x=1",
        ),
        ("", ""),
    ],
)
def test_canonical_url(raw: str, expected: str) -> None:
    assert canonical_url(raw) == expected


def test_canonical_url_is_idempotent() -> None:
    urls = [
        "https://youtu.be/abc?feature=share",
        "https://commons.wikimedia.org/wiki/Special:FilePath/Pasta.webm",
        "https://archive.org/details/foo/",
    ]
    for u in urls:
        once = canonical_url(u)
        twice = canonical_url(once)
        assert once == twice, u


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="src:x",
        source="src",
        source_native_id="x",
        url="https://example.test/x",
        title="How to make garlic butter pasta",
        description="",
        duration_s=300.0,
        height=1080,
        author="Alice",
        license=License.CC_BY,
        provenance=Provenance(
            extractor="t",
            extractor_git="deadbeef",
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            query="",
        ),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_bucket_key_collides_on_near_duplicates() -> None:
    a = _rec(id="a:1", url="https://a.example/1", duration_s=300.0, height=1080)
    b = _rec(id="b:1", url="https://b.example/2", duration_s=302.0, height=1080)
    assert bucket_key(a) == bucket_key(b)


def test_bucket_key_differs_on_different_author() -> None:
    a = _rec(id="a:1", url="https://a.example/1", author="Alice")
    b = _rec(id="b:1", url="https://b.example/2", author="Bob")
    assert bucket_key(a) != bucket_key(b)


def test_bucket_key_differs_on_different_title() -> None:
    a = _rec(id="a:1", url="https://a.example/1", title="How to make garlic butter pasta today")
    b = _rec(id="b:1", url="https://b.example/2", title="Sourdough starter from scratch tonight")
    assert bucket_key(a) != bucket_key(b)


def test_dedup_collapses_url_aliases() -> None:
    a = _rec(
        id="a:1",
        url="https://www.youtube.com/watch?v=abc123",
        license=License.RESTRICTED,
    )
    b = _rec(
        id="b:1",
        url="https://youtu.be/abc123?feature=share",
        license=License.CC_BY,
    )
    out = dedup([a, b])
    assert len(out) == 1
    assert out[0].license is License.CC_BY, "should prefer the redistributable record"


def test_dedup_is_stable_and_pure() -> None:
    records = [
        _rec(id="a:1", url="https://a.example/1"),
        _rec(id="b:1", url="https://b.example/1", title="Totally different title about knives"),
    ]
    once = dedup(records)
    twice = dedup(records)
    assert [r.id for r in once] == [r.id for r in twice]
    assert len(once) == 2
