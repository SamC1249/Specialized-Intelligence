"""Baseline regression checks.

`compare-to-baseline` reads a saved `reports/*.json` (produced by
`python -m specint compare`) and compares it to a freshly-run set of
rows. Regressions on `mean_quality`, `n_license_clean`, or
`total_duration_s` beyond the tolerance fail the check.

This is the mechanical enforcement of AGENTS.md's Comparison-First
rule: a new adapter or filter that regresses any of the frozen metrics
on the fixture suite must either raise the tolerance explicitly (with
a plan.md justification) or land as a follow-up PR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specint.records import BenchmarkResult

WATCHED_METRICS: tuple[str, ...] = (
    "mean_quality",
    "n_license_clean",
    "total_duration_s",
)


@dataclass(frozen=True)
class Delta:
    source: str
    metric: str
    baseline: float
    current: float
    delta: float
    regressed: bool


@dataclass
class RegressionReport:
    baseline_path: str
    tolerance_abs: float
    deltas: list[Delta] = field(default_factory=list)

    @property
    def regressions(self) -> list[Delta]:
        return [d for d in self.deltas if d.regressed]

    @property
    def ok(self) -> bool:
        return not self.regressions

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_path": self.baseline_path,
            "tolerance_abs": self.tolerance_abs,
            "ok": self.ok,
            "n_regressions": len(self.regressions),
            "deltas": [
                {
                    "source": d.source,
                    "metric": d.metric,
                    "baseline": d.baseline,
                    "current": d.current,
                    "delta": d.delta,
                    "regressed": d.regressed,
                }
                for d in self.deltas
            ],
        }


def _index_rows(rows: list[dict[str, Any]] | list[BenchmarkResult]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        data = row.model_dump(mode="json") if isinstance(row, BenchmarkResult) else row
        out[data["source"]] = {
            "mean_quality": float(data.get("mean_quality", 0.0)),
            "n_license_clean": float(data.get("n_license_clean", 0)),
            "total_duration_s": float(data.get("total_duration_s", 0.0)),
        }
    return out


def load_baseline(path: str | Path) -> dict[str, dict[str, float]]:
    payload = json.loads(Path(path).read_text())
    if "rows" not in payload or not isinstance(payload["rows"], list):
        raise ValueError(f"baseline {path} missing 'rows' list")
    return _index_rows(payload["rows"])


def compare_against_baseline(
    baseline_path: str | Path,
    current_rows: list[BenchmarkResult] | list[dict[str, Any]],
    *,
    tolerance_abs: float = 0.02,
) -> RegressionReport:
    baseline = load_baseline(baseline_path)
    current = _index_rows(current_rows)

    deltas: list[Delta] = []
    for source in sorted(set(baseline) | set(current)):
        b_row = baseline.get(source, {})
        c_row = current.get(source, {})
        for metric in WATCHED_METRICS:
            b_val = b_row.get(metric, 0.0)
            c_val = c_row.get(metric, 0.0)
            delta = c_val - b_val
            regressed = delta < -tolerance_abs
            deltas.append(
                Delta(
                    source=source,
                    metric=metric,
                    baseline=b_val,
                    current=c_val,
                    delta=delta,
                    regressed=regressed,
                )
            )
    return RegressionReport(
        baseline_path=str(baseline_path),
        tolerance_abs=tolerance_abs,
        deltas=deltas,
    )
