"""JSON round-trip guardrails for the canonical Pydantic models.

Any change that breaks JSON round-tripping (e.g. adding a non-JSON-safe
type without a serializer) will fail this test loudly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.fixtures import load_by_source
from specint.records import (
    BenchmarkResult,
    License,
    Provenance,
    SourceQuery,
    VideoRecord,
)


def test_source_query_roundtrip() -> None:
    q = SourceQuery(terms=["a", "b"], max_results=7, language="en")
    payload = q.model_dump(mode="json")
    assert SourceQuery.model_validate(payload) == q


def test_video_record_roundtrip() -> None:
    prov = Provenance(
        extractor="t",
        extractor_git="deadbeef",
        fetched_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        query="terms=a;max=1;lang=",
    )
    r = VideoRecord(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="hello",
        description="world",
        license=License.CC_BY,
        provenance=prov,
        keywords=["a", "b"],
        recipe_steps=["chop", "sear"],
    )
    payload = r.model_dump(mode="json")
    assert VideoRecord.model_validate(payload) == r


def test_benchmark_result_roundtrip() -> None:
    row = BenchmarkResult(
        source="foo",
        query_terms=["pasta", "sauce"],
        n_records=3,
        n_license_clean=2,
        total_duration_s=900.0,
        mean_quality=0.5,
        p50_quality=0.5,
        p90_quality=0.7,
        unique_authors=3,
        notes="x",
    )
    payload = row.model_dump(mode="json")
    assert BenchmarkResult.model_validate(payload) == row


def test_all_fixture_records_roundtrip(fixtures_dir: Path) -> None:
    query = SourceQuery(terms=["cooking"], max_results=10)
    by_source = load_by_source(query, fixtures_dir)
    for source, records in by_source.items():
        for r in records:
            payload = r.model_dump(mode="json")
            reloaded = VideoRecord.model_validate(payload)
            assert reloaded == r, f"{source}:{r.id} did not round-trip"


def test_provenance_is_immutable() -> None:
    from pydantic import ValidationError

    prov = Provenance(extractor="t", extractor_git="x", fetched_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        prov.extractor = "mutated"  # type: ignore[misc]


def test_harness_output_roundtrips(fixtures_dir: Path) -> None:
    query = SourceQuery(terms=["cooking", "recipe"])
    rows = run_comparison(query, load_by_source(query, fixtures_dir), notes="rt")
    for row in rows:
        BenchmarkResult.model_validate(row.model_dump(mode="json"))
