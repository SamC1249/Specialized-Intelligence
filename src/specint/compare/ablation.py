"""Quality-component ablation harness.

For a fixed ``SourceQuery`` and bundle of ``by_source -> [VideoRecord]``,
run the full ``compare`` harness:

  1. once with the production ``WEIGHTS`` (baseline);
  2. once *per component*, with that component's weight set to 0.

Emit a deterministic JSON payload with the baseline ``__total__`` row
and, for every component, the delta on ``mean_quality`` and on
``n_license_clean`` (so we know whether removing a component changes the
*set* of clean records or just their score).

This is the operationalisation of AGENTS.md's Comparison-First Rule for
*filters* (not just sources): we never re-weight in production without
first proving the new weight moves a defensible metric.
"""

from __future__ import annotations

from collections.abc import Mapping

from specint.compare.harness import run_comparison
from specint.quality.metrics import WEIGHTS
from specint.records import BenchmarkResult, SourceQuery, VideoRecord


def _total(rows: list[BenchmarkResult]) -> BenchmarkResult:
    for row in rows:
        if row.source == "__total__":
            return row
    return BenchmarkResult.empty("__total__", [])


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
) -> dict:
    """Return a JSON-serialisable ablation payload.

    Output shape::

        {
          "baseline":   <BenchmarkResult __total__ row as dict>,
          "components": {
            "license_clean":      {"mean_quality": .., "delta_mean": .., ...},
            ...
          }
        }
    """
    baseline_rows = run_comparison(query, by_source, notes=f"{notes}|baseline")
    baseline_total = _total(baseline_rows)

    components: dict[str, dict] = {}
    for component in WEIGHTS:
        weights = dict(WEIGHTS)
        weights[component] = 0.0
        rows = run_comparison(
            query,
            by_source,
            notes=f"{notes}|drop:{component}",
            weights=weights,
        )
        total = _total(rows)
        components[component] = {
            "mean_quality": total.mean_quality,
            "delta_mean": total.mean_quality - baseline_total.mean_quality,
            "n_license_clean": total.n_license_clean,
            "delta_license_clean": total.n_license_clean - baseline_total.n_license_clean,
            "p50_quality": total.p50_quality,
            "p90_quality": total.p90_quality,
        }

    return {
        "baseline": baseline_total.model_dump(mode="json"),
        "components": components,
        "weights": dict(WEIGHTS),
    }
