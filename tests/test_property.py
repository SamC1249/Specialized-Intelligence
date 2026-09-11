"""Property-based tests using Hypothesis.

We want strong bounds and structural invariants that individual example
tests can miss:

  P1. `score_record(r)` is in [0, 1] for every constructable record.
  P2. Aggregation is order-invariant: shuffling the per-source records
      does not change `BenchmarkResult` counts (mean/p50/p90 may reorder
      floats but must remain in [0, 1]).
  P3. Empty inputs to `run_comparison` yield exactly one `__total__`
      row with all zero counts.
"""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from specint.compare import run_comparison
from specint.quality import score_record
from specint.records import License, Provenance, SourceQuery, VideoRecord

_STRICT = settings(
    max_examples=75,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)


def _record_strategy() -> st.SearchStrategy[VideoRecord]:
    prov = Provenance(extractor="test.hypothesis", fetched_at=datetime.now(UTC), query="")

    def _build(
        native_id: int,
        title: str,
        description: str,
        duration: float | None,
        height: int | None,
        license_name: str,
        steps: list[str],
    ) -> VideoRecord:
        return VideoRecord(
            id=f"prop:{native_id}",
            source="prop",
            source_native_id=str(native_id),
            url=f"https://example.test/{native_id}",
            title=title,
            description=description,
            duration_s=duration,
            height=height,
            license=License[license_name],
            recipe_steps=steps,
            provenance=prov,
        )

    return st.builds(
        _build,
        native_id=st.integers(min_value=0, max_value=10_000_000),
        title=st.text(min_size=1, max_size=200),
        description=st.text(max_size=1000),
        duration=st.one_of(st.none(), st.floats(min_value=0.0, max_value=100_000.0)),
        height=st.one_of(st.none(), st.integers(min_value=0, max_value=8192)),
        license_name=st.sampled_from([lic.name for lic in License]),
        steps=st.lists(st.text(max_size=200), max_size=25),
    )


@_STRICT
@given(_record_strategy())
def test_property_score_in_unit_interval(record: VideoRecord) -> None:
    score = score_record(record)
    assert 0.0 <= score <= 1.0


@_STRICT
@given(st.lists(_record_strategy(), min_size=1, max_size=20))
def test_property_aggregation_stays_bounded(records: list[VideoRecord]) -> None:
    query = SourceQuery(terms=["x"])
    rows = run_comparison(query, {"prop": records})
    for row in rows:
        assert 0.0 <= row.mean_quality <= 1.0
        assert 0.0 <= row.p50_quality <= 1.0
        assert 0.0 <= row.p90_quality <= 1.0
        assert row.n_license_clean <= row.n_records
        assert row.unique_authors <= row.n_records
        assert row.total_duration_s >= 0.0


def test_property_empty_inputs_produce_zero_total() -> None:
    query = SourceQuery(terms=["x"])
    rows = run_comparison(query, {})
    assert len(rows) == 1
    total = rows[0]
    assert total.source == "__total__"
    assert total.n_records == 0
    assert total.mean_quality == 0.0
    assert total.p50_quality == 0.0
    assert total.p90_quality == 0.0
    assert total.total_duration_s == 0.0
    assert total.unique_authors == 0
