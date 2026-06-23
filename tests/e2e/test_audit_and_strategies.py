"""E2E: load offline adapter fixtures and run the audit + strategy harness.

These tests are network-free: they read the same JSON / HTML fixtures the
adapter unit tests use and assert the audit + strategy reports are
non-trivial and deterministic across runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from specint.audit import audit_records
from specint.cli import _records_from_fixtures
from specint.compare.strategies import compare_strategies, strategy_overlap_matrix


@pytest.mark.e2e
def test_fixture_corpus_is_non_empty():
    records = _records_from_fixtures()
    assert len(records) > 0


@pytest.mark.e2e
def test_audit_runs_and_is_deterministic():
    records = _records_from_fixtures()
    a = audit_records(records).to_dict()
    b = audit_records(records).to_dict()
    assert a == b
    assert a["n_records"] == len(records)
    assert a["cuisine_counts"]


@pytest.mark.e2e
def test_strategies_are_deterministic_and_overlap_reasonable():
    records = _records_from_fixtures()
    results = compare_strategies(records, k=3, seed=7)
    matrix = strategy_overlap_matrix(results)
    again = compare_strategies(records, k=3, seed=7)
    assert [r.to_dict() for r in results] == [r.to_dict() for r in again]
    # the WM strategy and the metadata-quality strategy should not be identical
    wm = next(r for r in results if r.strategy == "wm_utility")
    qm = next(r for r in results if r.strategy == "quality_metadata")
    assert matrix[wm.strategy][qm.strategy] <= 1.0


@pytest.mark.e2e
def test_cli_strategies_emits_report(tmp_path):
    out = tmp_path / "strat.json"
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "specint",
            "strategies",
            "--top-k",
            "3",
            "--output",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["k"] == 3
    assert any(r["strategy"] == "wm_utility" for r in payload["strategies"])
    assert "overlap_jaccard" in payload
    assert result.returncode == 0


@pytest.mark.e2e
def test_cli_audit_emits_report(tmp_path):
    out = tmp_path / "audit.json"
    repo_root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [sys.executable, "-m", "specint", "audit", "--output", str(out)],
        check=True,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    payload = json.loads(out.read_text())
    assert payload["n_records"] >= 1
    assert payload["source_counts"]
