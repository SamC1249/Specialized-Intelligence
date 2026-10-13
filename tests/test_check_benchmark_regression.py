"""Unit tests for the benchmark-regression gate script.

The script lives under scripts/ rather than src/specint/ so it is not a
proper package. We import it via importlib to keep the test code clean.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_benchmark_regression.py"


@pytest.fixture(scope="module")
def regression_module():
    spec = importlib.util.spec_from_file_location("check_benchmark_regression", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_benchmark_regression"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def baseline_payload() -> dict:
    return json.loads((REPO_ROOT / "reports" / "baseline-2026-06-20.json").read_text())


def test_identical_payloads_pass(regression_module, baseline_payload):
    code, messages = regression_module.compare(baseline_payload, baseline_payload)
    assert code == regression_module.EXIT_OK
    assert any("ok" in m for m in messages)


def test_missing_source_fails(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    candidate["rows"] = [r for r in candidate["rows"] if r["source"] != "wikimedia"]
    code, messages = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_MISSING_SOURCE
    assert any("MISSING" in m and "wikimedia" in m for m in messages)


def test_integer_regression_fails(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    for row in candidate["rows"]:
        if row["source"] == "wikimedia":
            row["n_records"] = row["n_records"] - 1
    code, messages = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_REGRESSION
    assert any("n_records" in m for m in messages)


def test_quality_within_tolerance_passes(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    for row in candidate["rows"]:
        row["mean_quality"] = row["mean_quality"] + 0.0005  # under default 1e-3
    code, _ = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_OK


def test_quality_outside_tolerance_fails(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    for row in candidate["rows"]:
        if row["source"] == "wikimedia":
            row["mean_quality"] = row["mean_quality"] - 0.05
    code, messages = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_REGRESSION
    assert any("mean_quality" in m and "wikimedia" in m for m in messages)


def test_duration_outside_tolerance_fails(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    for row in candidate["rows"]:
        if row["source"] == "archive_org":
            row["total_duration_s"] = row["total_duration_s"] + 10.0
    code, messages = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_REGRESSION
    assert any("total_duration_s" in m and "archive_org" in m for m in messages)


def test_new_source_is_informational_by_default(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    extra = deepcopy(candidate["rows"][0])
    extra["source"] = "europeana"
    candidate["rows"].append(extra)
    code, messages = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_OK
    assert any("NEW SOURCE" in m and "europeana" in m for m in messages)


def test_new_source_strict_mode_fails(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    extra = deepcopy(candidate["rows"][0])
    extra["source"] = "europeana"
    candidate["rows"].append(extra)
    code, _ = regression_module.compare(candidate, baseline_payload, strict_new_sources=True)
    assert code == regression_module.EXIT_NEW_SOURCE_STRICT


def test_notes_field_is_ignored(regression_module, baseline_payload):
    candidate = deepcopy(baseline_payload)
    for row in candidate["rows"]:
        row["notes"] = "ci-run-not-baseline"
    code, _ = regression_module.compare(candidate, baseline_payload)
    assert code == regression_module.EXIT_OK


def test_malformed_candidate_raises(regression_module):
    with pytest.raises(SystemExit) as info:
        regression_module.compare({"rows": "not a list"}, {"rows": []})
    assert info.value.code == regression_module.EXIT_MALFORMED
