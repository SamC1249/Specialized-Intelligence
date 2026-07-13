from datetime import UTC, datetime

from specint.quality import (
    canonical_key,
    deduplicate,
    hamming,
    pairwise_similar,
    simhash,
)
from specint.records import License, Provenance, VideoRecord


def _rec(id_: str, title: str, **overrides) -> VideoRecord:
    base = dict(
        id=id_,
        source="t",
        source_native_id=id_,
        url=f"https://example.test/{id_}",
        title=title,
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_canonical_key_normalises_title_and_duration_buckets():
    a = _rec("a", "How to Make Pasta!", author="Chef A", duration_s=310.0)
    b = _rec("b", "how to make pasta", author="chef a", duration_s=308.0)
    assert canonical_key(a) == canonical_key(b)


def test_simhash_identical_texts_have_distance_zero():
    h1 = simhash("caramelised onion soup with gruyere toast")
    h2 = simhash("caramelised onion soup with gruyere toast")
    assert h1 == h2
    assert hamming(h1, h2) == 0


def test_simhash_unrelated_texts_are_far():
    a = simhash("caramelised onion soup with gruyere toast french classic")
    b = simhash("laser cutting sheet metal in industrial fabrication workshop")
    assert hamming(a, b) > 10


def test_deduplicate_collapses_exact_duplicates_prefers_better_license():
    unknown = _rec(
        "a", "How to make pasta", author="Chef", duration_s=300.0, license=License.UNKNOWN
    )
    ccby = _rec("b", "How to make pasta", author="Chef", duration_s=302.0, license=License.CC_BY)
    result = deduplicate([unknown, ccby])
    assert len(result.kept) == 1
    assert result.kept[0].id == "b"
    assert "a" in result.absorbed["b"]


def test_deduplicate_collapses_near_duplicates():
    a = _rec(
        "a",
        "Caramelised onion soup with gruyere toast",
        description="A slow simmered classic French onion soup with thyme.",
        license=License.CC_BY,
    )
    b = _rec(
        "b",
        "Caramelised onion soup with gruyere toasts",
        description="A slow simmered classic French onion soup with thyme leaves.",
        license=License.CC_BY,
    )
    c = _rec(
        "c",
        "Laser cutting stainless steel in a fabrication shop",
        description="A workshop demonstration of an industrial cutting head.",
        license=License.CC_BY,
    )
    result = deduplicate([a, b, c], near_threshold=15)
    kept_ids = {r.id for r in result.kept}
    assert "c" in kept_ids
    assert len(result.kept) == 2


def test_pairwise_similar_returns_below_threshold_pairs():
    a = _rec(
        "a",
        "Caramelised onion soup with gruyere toast",
        description="A slow simmered classic French onion soup with thyme.",
    )
    b = _rec(
        "b",
        "Caramelised onion soup with gruyere toasts",
        description="A slow simmered classic French onion soup with thyme leaves.",
    )
    c = _rec("c", "welding a steel bracket in a workshop for industrial cutting demos")
    pairs = pairwise_similar([a, b, c], threshold=15)
    ids = {tuple(sorted([x, y])) for x, y, _ in pairs}
    assert ("a", "b") in ids
    assert not any("c" in pair for pair in ids)


def test_deduplicate_disable_near():
    a = _rec("a", "onion soup classic")
    b = _rec("b", "onion soup classic tweaked")
    result = deduplicate([a, b], near_threshold=0)
    assert {r.id for r in result.kept} == {"a", "b"}
