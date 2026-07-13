from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import dedupe_by_id_and_title, dedupe_stats
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    source: str,
    native_id: str,
    title: str,
    url: str,
    author: str | None = None,
    license_: License = License.CC_BY,
    quality: float | None = 0.5,
) -> VideoRecord:
    return VideoRecord(
        id=f"{source}:{native_id}",
        source=source,
        source_native_id=native_id,
        url=url,
        title=title,
        author=author,
        license=license_,
        provenance=Provenance(extractor="tests", fetched_at=datetime.now(UTC), query="q"),
        quality_score=quality,
    )


def test_dedupe_empty_input_returns_empty():
    assert dedupe_by_id_and_title([]) == []


def test_dedupe_exact_id_collisions_dropped():
    a = _rec(
        source="wikimedia", native_id="1", title="Pasta", url="https://commons.wikimedia.org/1"
    )
    b = _rec(
        source="wikimedia", native_id="1", title="Pasta", url="https://commons.wikimedia.org/1"
    )
    out = dedupe_by_id_and_title([a, b])
    assert len(out) == 1


def test_dedupe_normalized_title_plus_same_author_collapses():
    a = _rec(
        source="wikimedia",
        native_id="10",
        title="Chocolate Cake",
        url="https://commons.wikimedia.org/10",
        author="Chef A",
        quality=0.4,
    )
    b = _rec(
        source="archive_org",
        native_id="20",
        title="Chocolate  cake!",
        url="https://archive.org/details/20",
        author="chef a",
        quality=0.7,
    )
    out = dedupe_by_id_and_title([a, b])
    assert len(out) == 1
    assert out[0].quality_score == 0.7


def test_dedupe_same_title_different_author_and_host_preserved():
    a = _rec(
        source="wikimedia",
        native_id="30",
        title="Chocolate Cake",
        url="https://commons.wikimedia.org/30",
        author="Chef A",
    )
    b = _rec(
        source="archive_org",
        native_id="40",
        title="Chocolate Cake",
        url="https://archive.org/details/40",
        author="Chef B",
    )
    out = dedupe_by_id_and_title([a, b])
    assert len(out) == 2


def test_dedupe_stats_math():
    a = _rec(source="wikimedia", native_id="1", title="A", url="https://commons.wikimedia.org/1")
    b = _rec(source="wikimedia", native_id="1", title="A", url="https://commons.wikimedia.org/1")
    after = dedupe_by_id_and_title([a, b])
    stats = dedupe_stats([a, b], after)
    assert stats == {"n_before": 2, "n_after": 1, "n_collapsed": 1}
