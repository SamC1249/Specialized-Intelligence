"""Guard against the H5 regression: `python -m specint compare
--fixtures` must produce a real, non-zero report.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main


def test_cli_fixtures_produces_nonzero_records(tmp_path: Path):
    out = tmp_path / "compare.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "recipe",
            "--output",
            str(out),
            "--quiet",
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    rows = {row["source"]: row for row in payload["rows"]}
    assert "__total__" in rows
    assert rows["__total__"]["n_records"] > 0
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert slug in rows
        assert rows[slug]["n_records"] >= 1, f"{slug} returned no fixture records"


def test_cli_fixtures_scorer_switch_flips_reported_scorer(tmp_path: Path):
    out_v1 = tmp_path / "v1.json"
    out_v2 = tmp_path / "v2.json"
    assert main(["compare", "--fixtures", "--output", str(out_v1), "--quiet"]) == 0
    assert (
        main(
            [
                "compare",
                "--fixtures",
                "--scorer",
                "v2",
                "--output",
                str(out_v2),
                "--quiet",
            ]
        )
        == 0
    )
    a = json.loads(out_v1.read_text())
    b = json.loads(out_v2.read_text())
    assert a["scorer"] == "v1"
    assert b["scorer"] == "v2"
    a_totals = next(r for r in a["rows"] if r["source"] == "__total__")
    b_totals = next(r for r in b["rows"] if r["source"] == "__total__")
    # v2 and v1 should differ on the same fixtures — otherwise v2 is a
    # no-op and we would silently regress the plan.
    assert abs(a_totals["mean_quality"] - b_totals["mean_quality"]) > 1e-6


def test_cli_matrix_smoke(tmp_path: Path):
    out = tmp_path / "matrix.json"
    rc = main(
        [
            "matrix",
            "--fixtures",
            "--name",
            "smoke",
            "--output",
            str(out),
            "--quiet",
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["suite"]["name"] == "smoke"
    assert any(r["source"] == "__total__" for r in payload["rows"])
