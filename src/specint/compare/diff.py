"""Compute mechanical diffs between two comparison reports.

Given two `reports/*.json` payloads produced by the CLI, emit
per-source delta rows: change in `n_records`, `n_license_clean`,
`mean_quality`, etc. This is the "did we get better?" answer the
Adversarial-Agent asks for in the 2026-07-14 plans.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class DiffRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    n_records_delta: int
    n_license_clean_delta: int
    total_duration_s_delta: float
    mean_quality_delta: float
    p50_quality_delta: float
    p90_quality_delta: float
    unique_authors_delta: int
    n_duplicates_delta: int
    scorer_a: str
    scorer_b: str


def _index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["source"]: row for row in payload.get("rows", [])}


def _num(value: Any) -> float:
    return float(value or 0)


def _int(value: Any) -> int:
    return int(value or 0)


def diff_reports(a: dict[str, Any], b: dict[str, Any]) -> list[DiffRow]:
    """Compute b - a per source.

    Missing sources are treated as all-zero rows so an added source
    surfaces as a positive delta and a removed one as a negative
    delta.
    """
    left = _index(a)
    right = _index(b)
    sources = sorted(set(left) | set(right))
    rows: list[DiffRow] = []
    for source in sources:
        la = left.get(source, {})
        lb = right.get(source, {})
        rows.append(
            DiffRow(
                source=source,
                n_records_delta=_int(lb.get("n_records")) - _int(la.get("n_records")),
                n_license_clean_delta=_int(lb.get("n_license_clean"))
                - _int(la.get("n_license_clean")),
                total_duration_s_delta=_num(lb.get("total_duration_s"))
                - _num(la.get("total_duration_s")),
                mean_quality_delta=_num(lb.get("mean_quality")) - _num(la.get("mean_quality")),
                p50_quality_delta=_num(lb.get("p50_quality")) - _num(la.get("p50_quality")),
                p90_quality_delta=_num(lb.get("p90_quality")) - _num(la.get("p90_quality")),
                unique_authors_delta=_int(lb.get("unique_authors"))
                - _int(la.get("unique_authors")),
                n_duplicates_delta=_int(lb.get("n_duplicates")) - _int(la.get("n_duplicates")),
                scorer_a=str(la.get("scorer") or "v1"),
                scorer_b=str(lb.get("scorer") or "v1"),
            )
        )
    return rows
