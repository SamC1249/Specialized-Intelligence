"""Unit tests for cross-source metadata dedup."""

from __future__ import annotations

from specint.quality.dedup import (
    dedup_records,
    duration_bucket,
    metadata_digest,
    normalize_text,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    *,
    source: str,
    native: str,
    title: str,
    author: str | None,
    duration: float | None,
    quality: float = 0.5,
    license: License = License.CC_BY,
) -> VideoRecord:
    return VideoRecord(
        id=f"{source}:{native}",
        source=source,
        source_native_id=native,
        url=f"https://example.test/{source}/{native}",
        title=title,
        description="",
        duration_s=duration,
        license=license,
        author=author,
        provenance=Provenance(extractor="tests.test_dedup"),
        quality_score=quality,
    )


def test_normalize_text_is_stable_across_diacritics_and_case():
    assert normalize_text("Crème Brûlée!") == "creme brulee"
    assert normalize_text("  Multi   Space ") == "multi space"
    assert normalize_text(None) == ""
    assert normalize_text("") == ""


def test_duration_bucket_none_and_zero_do_not_collide():
    assert duration_bucket(None) == -1
    assert duration_bucket(0) == -1
    assert duration_bucket(15) == 1
    assert duration_bucket(45) == 2
    assert duration_bucket(300) == 10


def test_metadata_digest_is_stable_and_source_agnostic():
    a = _rec(source="wikimedia", native="1", title="Pasta Carbonara", author="Jane", duration=300)
    b = _rec(
        source="archive_org", native="x", title="pasta  CARBONARA", author="jane", duration=305
    )
    assert metadata_digest(a) == metadata_digest(b)


def test_dedup_collapses_cross_source_duplicates():
    a = _rec(
        source="wikimedia",
        native="1",
        title="Pasta Carbonara",
        author="Jane",
        duration=300,
        quality=0.9,
    )
    b = _rec(
        source="archive_org",
        native="x",
        title="pasta  CARBONARA",
        author="jane",
        duration=305,
        quality=0.3,
    )
    out = dedup_records([a, b])
    assert len(out) == 1
    assert out[0].source == "wikimedia"


def test_dedup_never_merges_records_missing_signal():
    a = _rec(source="wikimedia", native="1", title="", author=None, duration=None, quality=0.9)
    b = _rec(source="archive_org", native="x", title="", author=None, duration=None, quality=0.9)
    assert len(dedup_records([a, b])) == 2


def test_dedup_within_source_uses_native_id():
    same = _rec(source="peertube", native="uuid-1", title="Bread", author="B", duration=600)
    dup = _rec(source="peertube", native="uuid-1", title="Bread", author="B", duration=600)
    out = dedup_records([same, dup])
    assert len(out) == 1


def test_dedup_is_deterministic_on_ties():
    a = _rec(source="wikimedia", native="1", title="Pasta", author="J", duration=300, quality=0.5)
    b = _rec(source="archive_org", native="2", title="pasta", author="j", duration=300, quality=0.5)
    out_ab = dedup_records([a, b])
    out_ba = dedup_records([b, a])
    assert [r.id for r in out_ab] == [r.id for r in out_ba]
