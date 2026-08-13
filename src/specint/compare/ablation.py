"""Weight-vector ablation harness.

Adversarial motivation (see docs/plan-2026-08-13.md H5): today's
`DEFAULT_WEIGHTS` are asserted, not measured. Any future PR that
tweaks weights should be forced to prove it does not silently
degrade any single source's mean_quality relative to the baseline.

Design:

- Pure. No I/O. Deterministic. Given the same `by_source` input every
  weight variant sees the *same* underlying records; only the weight
  vector changes.
- Records are scored *once per variant* — we never fork a per-record
  RNG. Any observed difference in mean_quality is attributable purely
  to the weight vector.

The returned `AblationRun` list carries one row per (variant, source)
plus a `__total__` row per variant, matching the structure of a
regular comparison report so downstream tooling can eat both.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from specint.compare.harness import aggregate
from specint.quality import DEFAULT_WEIGHTS, score_records
from specint.records import BenchmarkResult, SourceQuery, VideoRecord


class AblationRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: str
    weights: dict[str, float]
    rows: list[BenchmarkResult]


def _default_variants() -> dict[str, dict[str, float]]:
    baseline = dict(DEFAULT_WEIGHTS)
    license_heavy = dict(DEFAULT_WEIGHTS)
    license_heavy["license_clean"] = 0.50
    license_heavy["duration"] = 0.10
    license_heavy["resolution"] = 0.15
    license_heavy["text_density"] = 0.07
    license_heavy["procedural_density"] = 0.10
    license_heavy["has_steps"] = 0.03
    license_heavy["language_match"] = 0.05

    procedural_heavy = dict(DEFAULT_WEIGHTS)
    procedural_heavy["license_clean"] = 0.25
    procedural_heavy["duration"] = 0.10
    procedural_heavy["resolution"] = 0.10
    procedural_heavy["text_density"] = 0.10
    procedural_heavy["procedural_density"] = 0.30
    procedural_heavy["has_steps"] = 0.05
    procedural_heavy["language_match"] = 0.10

    return {
        "baseline": baseline,
        "license_heavy": license_heavy,
        "procedural_heavy": procedural_heavy,
    }


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    variants: Mapping[str, Mapping[str, float]] | None = None,
) -> list[AblationRun]:
    variants_map: dict[str, dict[str, float]] = (
        {k: dict(v) for k, v in variants.items()} if variants else _default_variants()
    )

    out: list[AblationRun] = []
    for variant, weights in variants_map.items():
        rows: list[BenchmarkResult] = []
        all_scored: list[VideoRecord] = []
        for source in sorted(by_source.keys()):
            scored = score_records(
                by_source[source],
                weights=weights,
                target_language=query.language,
            )
            all_scored.extend(scored)
            rows.append(aggregate(source, query.terms, scored, notes=f"ablation:{variant}"))
        rows.append(
            aggregate("__total__", query.terms, all_scored, notes=f"ablation:{variant}")
        )
        out.append(AblationRun(variant=variant, weights=weights, rows=rows))
    return out


def ablation_matrix(runs: Iterable[AblationRun]) -> dict[str, Any]:
    """Compact JSON payload: variant × source → mean_quality."""
    matrix: dict[str, dict[str, float]] = {}
    for run in runs:
        matrix[run.variant] = {row.source: row.mean_quality for row in run.rows}
    return {
        "variants": [
            {"variant": r.variant, "weights": r.weights} for r in runs
        ],
        "mean_quality_matrix": matrix,
    }
