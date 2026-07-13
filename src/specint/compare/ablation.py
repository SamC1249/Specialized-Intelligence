"""Quality-weight ablation harness.

Any change to `specint.quality.metrics.WEIGHTS` must be justified against
the current baseline. This module operationalises that: it runs the
comparison harness under several preset weight vectors on the same
records and emits a `ReportBundle` whose JSON form is checked into
`reports/`.

Design:
  - `PRESETS` is a curated dict of named weight vectors that answer
    specific adversarial questions (e.g. "what if we ignored license
    entirely?"). Add new presets *only* alongside a plan entry.
  - `run_ablation` is a pure function: it takes `by_source` records,
    scores them under each preset via `score_records(..., weights=...)`,
    and calls `run_comparison` per preset. No global state is mutated.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specint.compare.harness import run_comparison
from specint.quality.metrics import WEIGHTS as BASELINE_WEIGHTS
from specint.records import SourceQuery, VideoRecord


def _no_license() -> dict[str, float]:
    w = dict(BASELINE_WEIGHTS)
    w["license_clean"] = 0.0
    return w


def _steps_heavy() -> dict[str, float]:
    w = dict(BASELINE_WEIGHTS)
    w["has_steps"] = 0.20
    w["procedural_density"] = 0.20
    w["text_density"] = 0.10
    return w


def _resolution_heavy() -> dict[str, float]:
    w = dict(BASELINE_WEIGHTS)
    w["resolution"] = 0.30
    w["duration"] = 0.15
    return w


def _equal_weights() -> dict[str, float]:
    n = len(BASELINE_WEIGHTS)
    return {k: 1.0 / n for k in BASELINE_WEIGHTS}


def _language_heavy() -> dict[str, float]:
    w = dict(BASELINE_WEIGHTS)
    w["language_confidence"] = 0.25
    return w


PRESETS: dict[str, dict[str, float]] = {
    "baseline": dict(BASELINE_WEIGHTS),
    "no_license": _no_license(),
    "steps_heavy": _steps_heavy(),
    "resolution_heavy": _resolution_heavy(),
    "equal_weights": _equal_weights(),
    "language_heavy": _language_heavy(),
}


def run_ablation(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    presets: Mapping[str, Mapping[str, float]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Return a JSON-serialisable report bundle across all presets."""
    presets = presets or PRESETS
    bundle: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "presets": {},
    }
    for name, weights in presets.items():
        rows = run_comparison(query, by_source, notes=notes, weights=weights)
        totals = next(r for r in rows if r.source == "__total__")
        bundle["presets"][name] = {
            "weights": dict(weights),
            "rows": [r.model_dump(mode="json") for r in rows],
            "total_mean_quality": totals.mean_quality,
            "total_n_license_clean": totals.n_license_clean,
        }
    return bundle
