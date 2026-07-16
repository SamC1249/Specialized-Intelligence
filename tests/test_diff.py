from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main
from specint.compare import diff_reports


def test_diff_reports_pure_function():
    a = {
        "rows": [
            {
                "source": "wikimedia",
                "n_records": 2,
                "n_license_clean": 2,
                "total_duration_s": 300.0,
                "mean_quality": 0.6,
                "p50_quality": 0.6,
                "p90_quality": 0.7,
                "unique_authors": 2,
                "n_duplicates": 0,
                "scorer": "v1",
            },
            {
                "source": "__total__",
                "n_records": 2,
                "n_license_clean": 2,
                "total_duration_s": 300.0,
                "mean_quality": 0.6,
                "p50_quality": 0.6,
                "p90_quality": 0.7,
                "unique_authors": 2,
                "n_duplicates": 0,
                "scorer": "v1",
            },
        ]
    }
    b = {
        "rows": [
            {
                "source": "wikimedia",
                "n_records": 3,
                "n_license_clean": 3,
                "total_duration_s": 500.0,
                "mean_quality": 0.65,
                "p50_quality": 0.65,
                "p90_quality": 0.75,
                "unique_authors": 3,
                "n_duplicates": 1,
                "scorer": "v2",
            },
            {
                "source": "__total__",
                "n_records": 3,
                "n_license_clean": 3,
                "total_duration_s": 500.0,
                "mean_quality": 0.65,
                "p50_quality": 0.65,
                "p90_quality": 0.75,
                "unique_authors": 3,
                "n_duplicates": 1,
                "scorer": "v2",
            },
        ]
    }
    rows = diff_reports(a, b)
    wiki = next(r for r in rows if r.source == "wikimedia")
    assert wiki.n_records_delta == 1
    assert wiki.n_license_clean_delta == 1
    assert wiki.total_duration_s_delta == 200.0
    assert wiki.n_duplicates_delta == 1
    assert wiki.scorer_a == "v1"
    assert wiki.scorer_b == "v2"


def test_diff_cli_writes_output(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"rows": [{"source": "x", "n_records": 1}]}))
    b.write_text(json.dumps({"rows": [{"source": "x", "n_records": 4}]}))
    out = tmp_path / "diff.json"
    rc = main(["diff", str(a), str(b), "--output", str(out), "--quiet"])
    assert rc == 0
    payload = json.loads(out.read_text())
    row = next(r for r in payload["rows"] if r["source"] == "x")
    assert row["n_records_delta"] == 3
