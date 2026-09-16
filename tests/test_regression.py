"""Baseline regression detection tests."""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare.regression import compare_against_baseline


def _write_report(path: Path, rows: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "query": {"terms": ["cooking"], "max_results": 25, "language": None},
                "rows": rows,
            },
            sort_keys=True,
        )
    )


def _row(source: str, mq: float, ndur: float, licn: int) -> dict:
    return {
        "source": source,
        "query_terms": ["cooking"],
        "n_records": 1,
        "n_license_clean": licn,
        "total_duration_s": ndur,
        "mean_quality": mq,
        "p50_quality": mq,
        "p90_quality": mq,
        "unique_authors": 1,
        "notes": "",
    }


def test_no_regression_when_equal(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    _write_report(baseline, [_row("wikimedia", 0.6, 100.0, 1)])
    report = compare_against_baseline(baseline, [_row("wikimedia", 0.6, 100.0, 1)])
    assert report.ok
    assert report.regressions == []


def test_regression_flagged_when_metric_drops(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    _write_report(baseline, [_row("wikimedia", 0.6, 100.0, 2)])
    report = compare_against_baseline(
        baseline,
        [_row("wikimedia", 0.4, 100.0, 2)],
        tolerance_abs=0.05,
    )
    assert not report.ok
    metrics = {d.metric for d in report.regressions}
    assert "mean_quality" in metrics


def test_regression_uses_absolute_tolerance(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    _write_report(baseline, [_row("wikimedia", 0.6, 100.0, 1)])
    report = compare_against_baseline(
        baseline,
        [_row("wikimedia", 0.585, 100.0, 1)],
        tolerance_abs=0.02,
    )
    assert report.ok


def test_regression_missing_source_treated_as_zero(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    _write_report(baseline, [_row("wikimedia", 0.6, 100.0, 2)])
    report = compare_against_baseline(baseline, [])
    assert not report.ok
    sources = {d.source for d in report.regressions}
    assert "wikimedia" in sources
