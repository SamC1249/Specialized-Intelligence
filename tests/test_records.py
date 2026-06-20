from datetime import UTC, datetime

from specint.records import (
    BenchmarkResult,
    License,
    Provenance,
    SourceQuery,
    VideoRecord,
)


def test_license_redistributable_set():
    assert License.CC0.is_redistributable
    assert License.CC_BY.is_redistributable
    assert License.CC_BY_SA.is_redistributable
    assert License.PUBLIC_DOMAIN.is_redistributable
    assert License.OTHER_FREE.is_redistributable
    assert not License.UNKNOWN.is_redistributable
    assert not License.RESTRICTED.is_redistributable


def test_video_record_with_quality_returns_new_instance():
    prov = Provenance(extractor="t", fetched_at=datetime.now(UTC), query="")
    r = VideoRecord(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="x",
        provenance=prov,
    )
    r2 = r.with_quality(0.42)
    assert r.quality_score is None
    assert r2.quality_score == 0.42
    assert r2.id == r.id


def test_source_query_serialize_deterministic():
    q1 = SourceQuery(terms=["a", "b"], max_results=10, language="en")
    q2 = SourceQuery(terms=["a", "b"], max_results=10, language="en")
    assert q1.serialize() == q2.serialize()
    assert "max=10" in q1.serialize()
    assert "lang=en" in q1.serialize()


def test_benchmark_empty():
    row = BenchmarkResult.empty("foo", ["pasta"], notes="hi")
    assert row.n_records == 0
    assert row.mean_quality == 0.0
    assert row.notes == "hi"
