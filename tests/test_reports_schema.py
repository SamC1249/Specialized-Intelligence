"""Every JSON file under `reports/` must round-trip through our Pydantic
models. Keeps the on-disk contract from silently drifting when someone
adds a new column to `BenchmarkResult`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from specint.records import BenchmarkResult, SourceQuery

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _report_json_files() -> list[Path]:
    if not REPORTS.exists():
        return []
    return sorted(p for p in REPORTS.glob("*.json") if p.is_file())


@pytest.mark.parametrize("report_path", _report_json_files(), ids=lambda p: p.name)
def test_report_matches_pydantic_contract(report_path: Path) -> None:
    payload = json.loads(report_path.read_text())
    assert isinstance(payload, dict), f"{report_path.name}: top-level must be a JSON object"
    assert "query" in payload, f"{report_path.name}: missing 'query' key"
    assert "rows" in payload, f"{report_path.name}: missing 'rows' key"

    try:
        SourceQuery.model_validate(payload["query"])
    except ValidationError as exc:
        pytest.fail(f"{report_path.name}: query does not match SourceQuery — {exc}")

    for i, row in enumerate(payload["rows"]):
        try:
            BenchmarkResult.model_validate(row)
        except ValidationError as exc:
            pytest.fail(f"{report_path.name}: row[{i}] invalid BenchmarkResult — {exc}")

    sources = [r["source"] for r in payload["rows"]]
    assert "__total__" in sources, f"{report_path.name}: no __total__ aggregate row"


def test_reports_directory_exists() -> None:
    assert REPORTS.exists(), "reports/ directory is the canonical on-disk artifact location"


def test_at_least_one_baseline_present() -> None:
    baselines = list(REPORTS.glob("baseline-*.json"))
    assert baselines, (
        "no baseline-YYYY-MM-DD.json under reports/ — the comparison "
        "ratchet requires at least one committed baseline."
    )
