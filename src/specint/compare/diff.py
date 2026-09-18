"""Regression-detection over two benchmark reports.

Given two JSON payloads produced by :func:`specint.cli._cmd_compare`,
compute per-source deltas for the metrics that matter most for training
data quality: ``n_records``, ``n_license_clean``, ``mean_quality`` and
``total_duration_s``.

A row is flagged as a regression when *both* of the following hold:

  * ``mean_quality`` drops by ``>= quality_tolerance`` (default 0.02), or
    ``n_license_clean`` decreases while ``n_records`` did not, or
    ``n_records`` drops by more than 20% relative to the baseline.
  * The source is not brand-new (i.e. it existed in the baseline).

The CLI returns a non-zero exit status when *any* row regresses so this
can wire into CI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

_METRICS = ("n_records", "n_license_clean", "mean_quality", "total_duration_s", "unique_authors")


@dataclass(frozen=True)
class DiffRow:
    source: str
    baseline: dict[str, float]
    current: dict[str, float]
    delta: dict[str, float]
    regressed: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        return payload


def _rows_by_source(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["source"]: row for row in payload.get("rows", []) if "source" in row}


def diff_reports(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    quality_tolerance: float = 0.02,
    record_drop_tolerance: float = 0.20,
) -> list[DiffRow]:
    base_rows = _rows_by_source(baseline)
    cur_rows = _rows_by_source(current)

    all_sources = sorted(set(base_rows) | set(cur_rows))
    out: list[DiffRow] = []
    for source in all_sources:
        b = base_rows.get(source, {})
        c = cur_rows.get(source, {})
        base_metrics = {m: float(b.get(m, 0.0) or 0.0) for m in _METRICS}
        cur_metrics = {m: float(c.get(m, 0.0) or 0.0) for m in _METRICS}
        delta = {m: cur_metrics[m] - base_metrics[m] for m in _METRICS}

        reasons: list[str] = []
        if source in base_rows:
            if -delta["mean_quality"] >= quality_tolerance:
                reasons.append(
                    f"mean_quality dropped {delta['mean_quality']:+.3f} (>= {quality_tolerance})"
                )
            if (
                cur_metrics["n_license_clean"] < base_metrics["n_license_clean"]
                and cur_metrics["n_records"] >= base_metrics["n_records"]
            ):
                reasons.append("n_license_clean dropped without a matching n_records drop")
            if base_metrics["n_records"] > 0:
                rel_drop = -delta["n_records"] / base_metrics["n_records"]
                if rel_drop >= record_drop_tolerance:
                    reasons.append(
                        f"n_records dropped {delta['n_records']:+.0f}"
                        f" ({rel_drop:.1%} >= {record_drop_tolerance:.0%})"
                    )
        regressed = bool(reasons)
        out.append(
            DiffRow(
                source=source,
                baseline=base_metrics,
                current=cur_metrics,
                delta=delta,
                regressed=regressed,
                reasons=tuple(reasons),
            )
        )
    return out


def summarize(rows: list[DiffRow]) -> str:
    lines = ["source\tΔ n_records\tΔ n_license_clean\tΔ mean_quality\tregressed"]
    for row in rows:
        lines.append(
            f"{row.source}\t"
            f"{row.delta['n_records']:+.0f}\t"
            f"{row.delta['n_license_clean']:+.0f}\t"
            f"{row.delta['mean_quality']:+.3f}\t"
            f"{'YES' if row.regressed else 'no'}"
        )
    return "\n".join(lines)


def any_regressed(rows: list[DiffRow]) -> bool:
    return any(r.regressed for r in rows)
