from datetime import UTC, datetime

from specint.compare import ParetoPoint, pareto_frontier, run_full_comparison
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(**kw) -> VideoRecord:
    base = dict(
        id="s:1",
        source="s",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking video",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(kw)
    return VideoRecord(**base)


def test_pareto_frontier_drops_dominated_sources():
    pts = [
        # `high_q` wins on quality/clean but has low yield
        ParetoPoint("high_q", mean_quality=0.9, license_clean_rate=1.0, unique_after_dedupe=3),
        # `high_yield` wins on yield but is dirtier
        ParetoPoint("high_yield", mean_quality=0.6, license_clean_rate=0.7, unique_after_dedupe=50),
        # dominated on every axis by `high_q`
        ParetoPoint("weak", mean_quality=0.4, license_clean_rate=0.5, unique_after_dedupe=2),
    ]
    frontier = pareto_frontier(pts)
    assert "weak" not in frontier
    assert set(frontier) == {"high_q", "high_yield"}


def test_run_full_comparison_backcompat_rows_shape():
    query = SourceQuery(terms=["x"])
    r = _rec(license=License.CC_BY, duration_s=100, height=720)
    result = run_full_comparison(query, {"src": [r]})
    row_sources = {row.source for row in result.rows}
    assert row_sources == {"src", "__total__"}
    assert result.dedupe_report is None
    assert result.pareto == ["src"]


def test_run_full_comparison_dedupe_and_language():
    query = SourceQuery(terms=["cooking"])
    a = _rec(
        id="wikimedia:1",
        source="wikimedia",
        title="Pasta Carbonara",
        author="Chef A",
        duration_s=300.0,
        license=License.CC_BY,
    )
    b = _rec(
        id="archive_org:1",
        source="archive_org",
        source_native_id="1",
        url="https://example.test/archive/1",
        title="Pasta Carbonara",
        author="Chef A",
        duration_s=302.0,
        license=License.CC0,
    )
    c = _rec(
        id="peertube:9",
        source="peertube",
        source_native_id="9",
        url="https://example.test/pt/9",
        title="Sourdough Loaves",
        description="Preheat the oven to 220C, then bake for 30 minutes.",
        license=License.CC_BY_SA,
    )
    by_source = {"wikimedia": [a], "archive_org": [b], "peertube": [c]}
    result = run_full_comparison(query, by_source, apply_dedupe=True, detect_language=True)
    dr = result.dedupe_report
    assert dr is not None
    assert dr.input_n == 3
    assert dr.output_n == 2
    total_deduped = next(r for r in result.rows if r.source == "__total_deduped__")
    total = next(r for r in result.rows if r.source == "__total__")
    assert total_deduped.n_records < total.n_records
    assert result.language_coverage["peertube"] >= 0.99
