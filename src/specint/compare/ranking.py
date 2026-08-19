"""Systematic scorer/pipeline comparison via Pareto dominance.

Given two `list[BenchmarkResult]` runs (each with a `__total__` row),
answer: does run B **strictly Pareto-dominate** run A on our headline
metrics? "Strictly" = >= on every metric, > on at least one.

Metrics (higher is better):
  - `mean_quality` (per-record weighted score)
  - `n_unique_after_dedup` (yield after dedup)
  - `n_license_clean`
  - `license_clean_ratio`
  - `mean_procedural_density`
  - number of languages seen

Also produces a `RankingDelta` for logging in reports/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from specint.records import BenchmarkResult

Verdict = Literal["dominates", "dominated", "tie", "mixed"]


def _row(rows: list[BenchmarkResult], source: str = "__total__") -> BenchmarkResult:
    for r in rows:
        if r.source == source:
            return r
    raise ValueError(f"no row for source={source} in benchmark result set")


@dataclass(frozen=True)
class RankingDelta:
    verdict: Verdict
    metrics: dict[str, tuple[float, float]]

    def as_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "metrics": {
                k: {"a": a, "b": b, "delta_b_minus_a": b - a} for k, (a, b) in self.metrics.items()
            },
        }


def compare_runs(
    a: list[BenchmarkResult], b: list[BenchmarkResult], source: str = "__total__"
) -> RankingDelta:
    ra, rb = _row(a, source), _row(b, source)
    metrics: dict[str, tuple[float, float]] = {
        "mean_quality": (ra.mean_quality, rb.mean_quality),
        "n_unique_after_dedup": (float(ra.n_unique_after_dedup), float(rb.n_unique_after_dedup)),
        "n_license_clean": (float(ra.n_license_clean), float(rb.n_license_clean)),
        "license_clean_ratio": (ra.license_clean_ratio, rb.license_clean_ratio),
        "mean_procedural_density": (ra.mean_procedural_density, rb.mean_procedural_density),
        "languages_seen": (float(len(ra.languages_seen)), float(len(rb.languages_seen))),
    }
    diffs = [round(b_v - a_v, 12) for (a_v, b_v) in metrics.values()]
    if all(d == 0 for d in diffs):
        verdict: Verdict = "tie"
    elif all(d >= 0 for d in diffs) and any(d > 0 for d in diffs):
        verdict = "dominates"
    elif all(d <= 0 for d in diffs) and any(d < 0 for d in diffs):
        verdict = "dominated"
    else:
        verdict = "mixed"
    return RankingDelta(verdict=verdict, metrics=metrics)
