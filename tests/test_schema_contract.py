"""Every JSON under `reports/` must round-trip through the Pydantic models.

Guarantees the on-disk contract described in `db_structured.md` cannot
drift silently. If a coding change breaks the schema, either the report
must be regenerated *and* the model bumped in the same PR, or the change
is a bug and this test catches it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.records import BenchmarkResult, SourceQuery

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

REPORT_FILES = sorted(p for p in REPORTS_DIR.glob("*.json") if p.name != ".gitkeep")


@pytest.mark.parametrize("report_path", REPORT_FILES, ids=lambda p: p.name)
def test_report_matches_pydantic_contract(report_path: Path) -> None:
    payload = json.loads(report_path.read_text())

    assert isinstance(payload, dict)
    assert set(payload.keys()) >= {"query", "rows"}, (
        f"{report_path.name}: expected top-level keys 'query' and 'rows', got {sorted(payload)}"
    )

    query = SourceQuery.model_validate(payload["query"])
    assert query.max_results > 0

    rows = payload["rows"]
    assert isinstance(rows, list) and rows, f"{report_path.name}: empty rows"

    parsed_rows = [BenchmarkResult.model_validate(r) for r in rows]
    assert any(r.source == "__total__" for r in parsed_rows), (
        f"{report_path.name}: missing __total__ aggregate row"
    )

    for row in parsed_rows:
        assert row.n_license_clean <= row.n_records
        assert row.n_records >= 0
        assert 0.0 <= row.mean_quality <= 1.0
        assert 0.0 <= row.p50_quality <= 1.0
        assert 0.0 <= row.p90_quality <= 1.0
        assert row.total_duration_s >= 0.0
        assert row.unique_authors >= 0


def test_reports_directory_is_tracked() -> None:
    assert REPORTS_DIR.is_dir(), "reports/ must exist as a checked-in directory"
    assert (REPORTS_DIR / ".gitkeep").exists() or REPORT_FILES, (
        "reports/ must be non-empty or carry a .gitkeep so CI can find it"
    )
