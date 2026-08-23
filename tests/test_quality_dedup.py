from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.dedup import dedup_records, dedup_stats, fingerprint
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking Pasta Carbonara",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_fingerprint_normalizes_title_and_duration():
    a = _rec(title="Cooking Pasta Carbonara!!!", duration_s=312.4)
    b = _rec(id="t:2", title="  cooking   pasta   carbonara ", duration_s=313.9)
    assert fingerprint(a) == fingerprint(b)


def test_dedup_collapses_cross_source_duplicates():
    a = _rec(
        id="wikimedia:100",
        source="wikimedia",
        title="Cooking Pasta Carbonara",
        duration_s=312.0,
        license=License.CC_BY_SA,
        quality_score=0.72,
    )
    b = _rec(
        id="archive_org:200",
        source="archive_org",
        title="cooking pasta carbonara",
        duration_s=310.5,
        license=License.CC_BY,
        quality_score=0.55,
    )
    c = _rec(
        id="peertube:xyz",
        source="peertube",
        title="Sourdough Bread From Scratch",
        duration_s=642.0,
        license=License.CC_BY_SA,
        quality_score=0.68,
    )
    out = dedup_records([a, b, c])
    assert len(out) == 2
    # a wins over b: same fingerprint, higher quality_score
    ids = {r.id for r in out}
    assert "wikimedia:100" in ids
    assert "peertube:xyz" in ids
    assert "archive_org:200" not in ids


def test_dedup_prefers_license_clean_over_restricted():
    good = _rec(
        id="wikimedia:1", title="Recipe X", duration_s=100.0, license=License.CC0, quality_score=0.4
    )
    bad = _rec(
        id="archive_org:1",
        source="archive_org",
        title="Recipe X",
        duration_s=101.0,
        license=License.RESTRICTED,
        quality_score=0.99,
    )
    [only] = dedup_records([bad, good])
    assert only.id == "wikimedia:1"


def test_dedup_stats_returns_before_after():
    a = _rec(id="a", title="Same", duration_s=100.0)
    b = _rec(id="b", title="Same", duration_s=100.0)
    c = _rec(id="c", title="Different", duration_s=200.0)
    before, after = dedup_stats([a, b, c])
    assert before == 3
    assert after == 2


def test_dedup_preserves_unmergeable_records():
    a = _rec(id="a", title="", duration_s=None)
    b = _rec(id="b", title="", duration_s=None)
    out = dedup_records([a, b])
    assert {r.id for r in out} == {"a", "b"}
