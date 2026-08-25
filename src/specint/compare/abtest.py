"""Paired A/B benchmark: baseline weights vs experimental weights.

Runs the same input records through the harness twice, using two weight
dicts, and emits a paired JSON report suitable for `reports/` review.
The report is deterministic given the same input records and weight
dicts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specint.compare.harness import run_comparison
from specint.quality.metrics import score_records
from specint.records import BenchmarkResult, SourceQuery, VideoRecord


def _dump(rows: list[BenchmarkResult]) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in rows]


def run_ab_test(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    baseline_weights: Mapping[str, float],
    experimental_weights: Mapping[str, float],
    notes: str = "",
) -> dict[str, Any]:
    """Score input records under both weight dicts and return a paired report.

    Returns a dict with:
      - ``baseline.rows`` / ``experimental.rows`` — full row lists from
        the harness (per-source + `__total__` + `__deduped__`).
      - ``license_clean_delta.mean_quality`` — signed delta on the
        `__deduped__` row's `mean_quality`. Positive means experimental
        beats baseline.
      - ``winner`` — one of ``"baseline"``, ``"experimental"``, ``"tie"``.
    """

    def _scored(weights: Mapping[str, float]):
        return {slug: score_records(recs, weights=weights) for slug, recs in by_source.items()}

    def _scorer_factory(weights: Mapping[str, float]):
        return lambda records: score_records(records, weights=weights)

    baseline_rows = run_comparison(
        query,
        _scored(baseline_weights),
        notes=(notes + " weights=baseline").strip(),
        scorer=_scorer_factory(baseline_weights),
    )
    experimental_rows = run_comparison(
        query,
        _scored(experimental_weights),
        notes=(notes + " weights=experimental").strip(),
        scorer=_scorer_factory(experimental_weights),
    )
    baseline_dedup = next(r for r in baseline_rows if r.source == "__deduped__")
    exp_dedup = next(r for r in experimental_rows if r.source == "__deduped__")
    delta = exp_dedup.mean_quality - baseline_dedup.mean_quality
    winner = "tie" if abs(delta) < 1e-6 else ("experimental" if delta > 0 else "baseline")

    return {
        "query": query.model_dump(mode="json"),
        "baseline": {
            "weights": dict(baseline_weights),
            "rows": _dump(baseline_rows),
        },
        "experimental": {
            "weights": dict(experimental_weights),
            "rows": _dump(experimental_rows),
        },
        "delta": {
            "deduped_mean_quality": delta,
            "deduped_n_records_baseline": baseline_dedup.n_records,
            "deduped_n_records_experimental": exp_dedup.n_records,
        },
        "winner": winner,
    }
