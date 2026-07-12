"""Quality-scorer ablation.

We measure the marginal contribution of each v2 component *and*
compare v2 to v1 on a small procedural-density ground-truth
proxy. Ground truth is intentionally weak (we do not have human
labels), but it must be:

    - deterministic (same fixture in → same numbers out),
    - and defensible.

We define `good` per record as:

    - `license.is_redistributable` AND
    - `duration_s` is not None AND 60 <= duration_s <= 1800 AND
    - `len(recipe_steps) >= 3`.

For each scorer variant we compute:

    - `mean_good`: mean quality of good records,
    - `mean_bad`: mean quality of the rest,
    - `separation`: mean_good - mean_bad (higher is better),
    - `kendall_tau`: Kendall's τ between the scorer's ranking and the
      binary ground-truth (0/1) ranking (higher is better).

Variants:

    - `v1`: `score_record_v1` (2026-06-20 baseline scorer).
    - `v2`: `score_record_v2` with the default `WEIGHTS_V2`.
    - `v2_drop_<component>`: v2 with that component's weight zeroed and
      the remaining weights re-normalised.
"""

from __future__ import annotations

from statistics import fmean
from typing import Any

from specint.domains import DEFAULT_DOMAIN, Domain
from specint.quality.metrics import (
    WEIGHTS_V2,
    score_record_v1,
    score_record_v2,
)
from specint.records import VideoRecord


def _is_good(record: VideoRecord) -> bool:
    if not record.license.is_redistributable:
        return False
    if record.duration_s is None:
        return False
    if not (60.0 <= record.duration_s <= 1800.0):
        return False
    return len(record.recipe_steps) >= 3


def _kendall_tau(scores: list[float], labels: list[int]) -> float:
    n = len(scores)
    if n < 2:
        return 0.0
    concordant = 0
    discordant = 0
    ties = 0
    for i in range(n):
        for j in range(i + 1, n):
            ds = scores[i] - scores[j]
            dl = labels[i] - labels[j]
            if ds == 0 or dl == 0:
                ties += 1
                continue
            if (ds > 0) == (dl > 0):
                concordant += 1
            else:
                discordant += 1
    total = concordant + discordant + ties
    if total == 0:
        return 0.0
    return (concordant - discordant) / total


def _stats(scores: list[float], labels: list[int]) -> dict[str, float]:
    good = [s for s, y in zip(scores, labels, strict=True) if y == 1]
    bad = [s for s, y in zip(scores, labels, strict=True) if y == 0]
    mean_good = fmean(good) if good else 0.0
    mean_bad = fmean(bad) if bad else 0.0
    return {
        "n": float(len(scores)),
        "n_good": float(len(good)),
        "mean_good": mean_good,
        "mean_bad": mean_bad,
        "separation": mean_good - mean_bad,
        "kendall_tau": _kendall_tau(scores, labels),
    }


def _drop_weights(component: str) -> dict[str, float]:
    return {k: (0.0 if k == component else v) for k, v in WEIGHTS_V2.items()}


def run_ablation(
    records: list[VideoRecord],
    domain: Domain = DEFAULT_DOMAIN,
) -> dict[str, Any]:
    labels = [1 if _is_good(r) else 0 for r in records]

    variants: dict[str, list[float]] = {
        "v1": [score_record_v1(r) for r in records],
        "v2": [score_record_v2(r, domain=domain) for r in records],
    }
    for component in WEIGHTS_V2:
        weights = _drop_weights(component)
        variants[f"v2_drop_{component}"] = [
            score_record_v2(r, domain=domain, weights=weights) for r in records
        ]

    return {
        "domain": domain.slug,
        "n_records": len(records),
        "n_good": sum(labels),
        "variants": {name: _stats(scores, labels) for name, scores in variants.items()},
    }


__all__ = ["run_ablation"]
