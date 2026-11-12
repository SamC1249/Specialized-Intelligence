"""Tests for scripts/check_baseline_regression.py.

The gate is only useful if it (a) passes on the committed baseline and
(b) fails on a hand-crafted regression. Both are asserted here so the
gate itself cannot silently rot.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = REPO_ROOT / "scripts" / "check_baseline_regression.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("baseline_gate", GATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def gate():
    return _load_gate()


def test_gate_passes_against_committed_baseline(gate) -> None:
    violations = gate.check(
        baseline_path=gate.DEFAULT_BASELINE,
        allow_quality_regression=False,
        quality_tolerance=0.02,
    )
    assert violations == [], (
        "committed baseline should pass the gate; if this fires without "
        "a deliberate scoring change, something has regressed."
    )


def test_gate_fires_on_n_license_clean_regression(gate, tmp_path: Path) -> None:
    baseline = json.loads(gate.DEFAULT_BASELINE.read_text())
    for row in baseline["rows"]:
        if row["source"] != "__total__":
            row["n_license_clean"] = row["n_license_clean"] + 5
    fake = tmp_path / "baseline-inflated.json"
    fake.write_text(json.dumps(baseline))

    violations = gate.check(
        baseline_path=fake,
        allow_quality_regression=False,
        quality_tolerance=0.02,
    )
    assert violations, "gate must fire when n_license_clean regresses"
    assert any("n_license_clean regressed" in v for v in violations)


def test_gate_fires_on_mean_quality_regression(gate, tmp_path: Path) -> None:
    baseline = json.loads(gate.DEFAULT_BASELINE.read_text())
    for row in baseline["rows"]:
        if row["source"] != "__total__":
            row["mean_quality"] = min(1.0, row["mean_quality"] + 0.20)
    fake = tmp_path / "baseline-inflated-quality.json"
    fake.write_text(json.dumps(baseline))

    violations = gate.check(
        baseline_path=fake,
        allow_quality_regression=False,
        quality_tolerance=0.02,
    )
    assert any("mean_quality regressed" in v for v in violations)


def test_gate_allows_quality_regression_when_flag_set(gate, tmp_path: Path) -> None:
    baseline = json.loads(gate.DEFAULT_BASELINE.read_text())
    for row in baseline["rows"]:
        if row["source"] != "__total__":
            row["mean_quality"] = min(1.0, row["mean_quality"] + 0.20)
    fake = tmp_path / "baseline-inflated-quality-2.json"
    fake.write_text(json.dumps(baseline))

    violations = gate.check(
        baseline_path=fake,
        allow_quality_regression=True,
        quality_tolerance=0.02,
    )
    # n_license_clean regressions still fire regardless of the quality flag,
    # so we assert only that quality-related violations are gone.
    assert not any("mean_quality regressed" in v for v in violations)


def test_gate_flags_missing_baseline(gate, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.json"
    violations = gate.check(
        baseline_path=missing,
        allow_quality_regression=False,
        quality_tolerance=0.02,
    )
    assert any("baseline file not found" in v for v in violations)
