"""End-to-end tests for the `compare-to-baseline` CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main


def _make_baseline(path: Path) -> None:
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "recipe",
            "--output",
            str(path),
        ]
    )
    assert rc == 0


def test_compare_to_baseline_ok_when_same_inputs(tmp_path: Path, capsys):
    baseline = tmp_path / "baseline.json"
    _make_baseline(baseline)
    out = tmp_path / "diff.json"
    rc = main(
        [
            "compare-to-baseline",
            "--baseline",
            str(baseline),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["ok"] is True
    assert payload["n_regressions"] == 0


def test_compare_to_baseline_fails_when_baseline_missing(tmp_path: Path):
    rc = main(["compare-to-baseline", "--baseline", str(tmp_path / "nope.json")])
    assert rc == 2


def test_compare_to_baseline_detects_regression(tmp_path: Path):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "query": {"terms": ["cooking"], "max_results": 25, "language": None},
                "rows": [
                    {
                        "source": "wikimedia",
                        "query_terms": ["cooking"],
                        "n_records": 5,
                        "n_license_clean": 99,
                        "total_duration_s": 9999.0,
                        "mean_quality": 0.99,
                        "p50_quality": 0.99,
                        "p90_quality": 0.99,
                        "unique_authors": 5,
                        "notes": "",
                    }
                ],
            }
        )
    )
    out = tmp_path / "diff.json"
    rc = main(
        [
            "compare-to-baseline",
            "--baseline",
            str(baseline),
            "--output",
            str(out),
        ]
    )
    assert rc == 1
    payload = json.loads(out.read_text())
    assert payload["ok"] is False
    assert payload["n_regressions"] > 0
