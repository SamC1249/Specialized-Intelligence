"""Report-to-report diff.

Two `reports/*.json` documents share the same schema; we compare them
row-by-row on `source` and emit a per-source delta so we can answer
"did the latest change help?" mechanically instead of by eyeball.

The diff output is intentionally *thin*: a list of `DiffRow`. Downstream
tools can render it as text, HTML, or a badge. This module has no I/O
apart from `load_report`.
"""

from __future__ import annotations

import json
from pathlib import Path
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
    baseline_scorer: str = "v1"
    candidate_scorer: str = "v1"
    verdict: str = "same"


def load_report(path: str | Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(Path(path).read_text())
    if "rows" not in data:
        raise ValueError(f"{path}: not a report (missing 'rows')")
    return data


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        src = row.get("source")
        if isinstance(src, str):
            out[src] = row
    return out


def _verdict(mean_delta: float, license_delta: int) -> str:
    if license_delta < 0:
        return "regressed_license"
    if mean_delta > 0.005:
        return "improved"
    if mean_delta < -0.005:
        return "regressed_quality"
    return "same"


def diff_reports(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[DiffRow]:
    base_idx = _index(baseline.get("rows") or [])
    cand_idx = _index(candidate.get("rows") or [])

    sources = sorted(set(base_idx) | set(cand_idx))
    out: list[DiffRow] = []
    empty: dict[str, Any] = {}
    for src in sources:
        b = base_idx.get(src) or empty
        c = cand_idx.get(src) or empty

        n_records_delta = int(c.get("n_records", 0)) - int(b.get("n_records", 0))
        n_license_delta = int(c.get("n_license_clean", 0)) - int(b.get("n_license_clean", 0))
        dur_delta = float(c.get("total_duration_s", 0.0)) - float(b.get("total_duration_s", 0.0))
        mean_delta = float(c.get("mean_quality", 0.0)) - float(b.get("mean_quality", 0.0))
        p50_delta = float(c.get("p50_quality", 0.0)) - float(b.get("p50_quality", 0.0))
        p90_delta = float(c.get("p90_quality", 0.0)) - float(b.get("p90_quality", 0.0))
        authors_delta = int(c.get("unique_authors", 0)) - int(b.get("unique_authors", 0))
        dup_delta = int(c.get("n_duplicates", 0)) - int(b.get("n_duplicates", 0))

        out.append(
            DiffRow(
                source=src,
                n_records_delta=n_records_delta,
                n_license_clean_delta=n_license_delta,
                total_duration_s_delta=dur_delta,
                mean_quality_delta=mean_delta,
                p50_quality_delta=p50_delta,
                p90_quality_delta=p90_delta,
                unique_authors_delta=authors_delta,
                n_duplicates_delta=dup_delta,
                baseline_scorer=str(b.get("scorer", "v1")) if b else "missing",
                candidate_scorer=str(c.get("scorer", "v1")) if c else "missing",
                verdict=_verdict(mean_delta, n_license_delta),
            )
        )
    return out
