"""Tests for the report-diff module."""

from __future__ import annotations

import json
import math
from pathlib import Path

from specint.compare.diff import diff_reports, load_report


def _report(source: str, mean: float, n_records: int, n_license_clean: int, scorer: str = "v1"):
    return {
        "query": {"terms": ["cooking"], "max_results": 25, "language": None},
        "rows": [
            {
                "source": source,
                "query_terms": ["cooking"],
                "n_records": n_records,
                "n_license_clean": n_license_clean,
                "total_duration_s": 100.0,
                "mean_quality": mean,
                "p50_quality": mean,
                "p90_quality": mean,
                "unique_authors": n_records,
                "notes": "",
                "n_duplicates": 0,
                "scorer": scorer,
            }
        ],
    }


def test_diff_reports_improvement_verdict():
    base = _report("wikimedia", 0.5, 2, 2)
    cand = _report("wikimedia", 0.7, 2, 2, scorer="v2")
    rows = diff_reports(base, cand)
    assert len(rows) == 1
    assert math.isclose(rows[0].mean_quality_delta, 0.2, abs_tol=1e-9)
    assert rows[0].verdict == "improved"
    assert rows[0].baseline_scorer == "v1"
    assert rows[0].candidate_scorer == "v2"


def test_diff_reports_license_regression_beats_quality_gain():
    base = _report("wikimedia", 0.5, 2, 2)
    cand = _report("wikimedia", 0.9, 2, 1, scorer="v2")
    rows = diff_reports(base, cand)
    assert rows[0].verdict == "regressed_license"


def test_diff_reports_handles_missing_source():
    base = _report("wikimedia", 0.5, 2, 2)
    cand_data = _report("wikimedia", 0.5, 2, 2)
    cand_data["rows"].append(dict(base["rows"][0], source="new_source"))
    rows = diff_reports(base, cand_data)
    sources = {r.source for r in rows}
    assert sources == {"wikimedia", "new_source"}


def test_load_report_rejects_non_report(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"not": "a report"}))
    try:
        load_report(p)
    except ValueError as e:
        assert "not a report" in str(e)
    else:
        raise AssertionError("expected ValueError")
