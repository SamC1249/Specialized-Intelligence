"""Weight-vector ablation harness.

Runs the *same* by_source fixture set against N different weight
vectors and emits a matrix report so weight-tuning PRs can prove they
beat the baseline. The input records are frozen once; each variant
re-scores from the same base to prevent randomness / order effects
polluting comparisons.

Output: a list of `AblationRow` dicts. `to_report` renders a JSON-safe
payload suitable for `reports/ablate-YYYY-MM-DD.json`.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping
from typing import Any

from specint.quality import score_records
from specint.quality.metrics import WEIGHTS
from specint.records import SourceQuery, VideoRecord

BASELINE_NAME = "baseline"
LANGUAGE_HEAVY_NAME = "language_heavy"
LICENSE_HEAVY_NAME = "license_heavy"
PROCEDURAL_HEAVY_NAME = "procedural_heavy"


PRESETS: dict[str, dict[str, float]] = {
    BASELINE_NAME: dict(WEIGHTS),
    LANGUAGE_HEAVY_NAME: {
        "license_clean": 0.25,
        "duration": 0.10,
        "resolution": 0.15,
        "text_density": 0.15,
        "has_steps": 0.10,
        "language_confidence": 0.25,
    },
    LICENSE_HEAVY_NAME: {
        "license_clean": 0.55,
        "duration": 0.10,
        "resolution": 0.15,
        "text_density": 0.10,
        "has_steps": 0.10,
    },
    PROCEDURAL_HEAVY_NAME: {
        "license_clean": 0.25,
        "duration": 0.10,
        "resolution": 0.15,
        "text_density": 0.20,
        "has_steps": 0.30,
    },
}


def ablate(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    presets: Mapping[str, Mapping[str, float]] | None = None,
) -> list[dict[str, Any]]:
    presets = presets or PRESETS
    rows: list[dict[str, Any]] = []
    for name, weights in presets.items():
        for source, records in sorted(by_source.items()):
            scored = score_records(records, weights=weights)
            qualities = [r.quality_score or 0.0 for r in scored]
            if qualities:
                mean_q = float(statistics.fmean(qualities))
                p90 = sorted(qualities)[max(0, round(0.9 * (len(qualities) - 1)))]
            else:
                mean_q = 0.0
                p90 = 0.0
            rows.append(
                {
                    "preset": name,
                    "source": source,
                    "n_records": len(scored),
                    "mean_quality": mean_q,
                    "p90_quality": p90,
                    "weights": dict(weights),
                }
            )
    return rows


def to_report(
    query: SourceQuery,
    ablation_rows: list[dict[str, Any]],
    notes: str = "",
) -> dict[str, Any]:
    presets = sorted({r["preset"] for r in ablation_rows})
    per_preset: dict[str, float] = {}
    for name in presets:
        rows = [r for r in ablation_rows if r["preset"] == name]
        qs = [r["mean_quality"] for r in rows]
        per_preset[name] = float(statistics.fmean(qs)) if qs else 0.0

    winner = max(per_preset.items(), key=lambda kv: kv[1]) if per_preset else (None, 0.0)
    return {
        "query": query.model_dump(mode="json"),
        "notes": notes,
        "rows": ablation_rows,
        "summary": {
            "per_preset_mean_quality": per_preset,
            "winner": {"preset": winner[0], "mean_quality": winner[1]},
        },
    }
