"""Deterministic diff between two compare-report JSON payloads."""

from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main
from specint.compare import diff_reports


def _row(source: str, **kw) -> dict:
    base = {
        "source": source,
        "query_terms": ["cooking"],
        "n_records": 0,
        "n_license_clean": 0,
        "total_duration_s": 0.0,
        "mean_quality": 0.0,
        "p50_quality": 0.0,
        "p90_quality": 0.0,
        "unique_authors": 0,
        "notes": "",
    }
    base.update(kw)
    return base


def test_diff_tracks_per_source_deltas_and_set_changes() -> None:
    a = {
        "query": {"terms": ["cooking"], "max_results": 10, "language": None},
        "rows": [
            _row("wikimedia", n_records=2, mean_quality=0.5, total_duration_s=100.0),
            _row("archive_org", n_records=3, mean_quality=0.3, total_duration_s=50.0),
        ],
    }
    b = {
        "query": {"terms": ["cooking"], "max_results": 10, "language": None},
        "rows": [
            _row("wikimedia", n_records=4, mean_quality=0.6, total_duration_s=200.0),
            _row("youtube_cc", n_records=5, mean_quality=0.7, total_duration_s=300.0),
        ],
    }

    report = diff_reports(a, b)

    assert report["added_sources"] == ["youtube_cc"]
    assert report["removed_sources"] == ["archive_org"]

    by_src = {s["source"]: s for s in report["sources"]}
    assert by_src["wikimedia"]["delta"]["n_records"] == 2
    assert by_src["wikimedia"]["delta"]["mean_quality"] == 0.1
    assert by_src["wikimedia"]["delta"]["total_duration_s"] == 100.0

    assert by_src["youtube_cc"]["delta"]["n_records"] == 5
    assert by_src["youtube_cc"]["a"] is None
    assert by_src["archive_org"]["b"] is None


def test_diff_cli_writes_output(tmp_path: Path) -> None:
    a = {"query": {}, "rows": [_row("wikimedia", n_records=1)]}
    b = {"query": {}, "rows": [_row("wikimedia", n_records=4)]}
    a_path = tmp_path / "a.json"
    b_path = tmp_path / "b.json"
    out_path = tmp_path / "diff.json"
    a_path.write_text(json.dumps(a))
    b_path.write_text(json.dumps(b))

    rc = main(["diff", str(a_path), str(b_path), "--output", str(out_path)])
    assert rc == 0

    payload = json.loads(out_path.read_text())
    assert payload["sources"][0]["delta"]["n_records"] == 3
