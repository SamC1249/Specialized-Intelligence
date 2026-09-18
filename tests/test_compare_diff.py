import json
from pathlib import Path

from specint.cli import main
from specint.compare import any_regressed, diff_reports


def _report(rows: list[dict]) -> dict:
    return {"query": {"terms": ["cooking"]}, "rows": rows}


def _row(**kwargs) -> dict:
    base = {
        "source": "wikimedia",
        "n_records": 10,
        "n_license_clean": 8,
        "mean_quality": 0.6,
        "p50_quality": 0.6,
        "p90_quality": 0.7,
        "total_duration_s": 3000.0,
        "unique_authors": 5,
        "query_terms": ["cooking"],
        "notes": "",
    }
    base.update(kwargs)
    return base


def test_diff_reports_flags_mean_quality_regression():
    baseline = _report([_row(mean_quality=0.60)])
    current = _report([_row(mean_quality=0.50)])
    rows = diff_reports(baseline, current, quality_tolerance=0.05)
    assert any_regressed(rows)
    assert rows[0].reasons[0].startswith("mean_quality dropped")


def test_diff_reports_flags_license_clean_drop():
    baseline = _report([_row(n_records=10, n_license_clean=10)])
    current = _report([_row(n_records=10, n_license_clean=6)])
    rows = diff_reports(baseline, current)
    assert any_regressed(rows)
    assert any("n_license_clean" in r for r in rows[0].reasons)


def test_diff_reports_flags_large_record_drop():
    baseline = _report([_row(n_records=10)])
    current = _report([_row(n_records=6)])
    rows = diff_reports(baseline, current, record_drop_tolerance=0.20)
    assert any_regressed(rows)


def test_diff_reports_new_source_is_not_a_regression():
    baseline = _report([_row(source="wikimedia")])
    current = _report([_row(source="wikimedia"), _row(source="youtube_cc", n_records=5)])
    rows = diff_reports(baseline, current)
    yt = next(r for r in rows if r.source == "youtube_cc")
    assert not yt.regressed


def test_diff_cli_writes_json_and_returns_zero_when_clean(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    out_path = tmp_path / "diff.json"

    baseline_path.write_text(json.dumps(_report([_row(mean_quality=0.60)])))
    current_path.write_text(json.dumps(_report([_row(mean_quality=0.61)])))

    rc = main(
        [
            "compare-diff",
            str(baseline_path),
            str(current_path),
            "--output",
            str(out_path),
            "--strict",
        ]
    )
    assert rc == 0
    payload = json.loads(out_path.read_text())
    assert payload["regressed"] is False


def test_diff_cli_strict_returns_one_on_regression(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(json.dumps(_report([_row(mean_quality=0.60)])))
    current_path.write_text(json.dumps(_report([_row(mean_quality=0.30)])))
    rc = main(
        [
            "compare-diff",
            str(baseline_path),
            str(current_path),
            "--strict",
        ]
    )
    assert rc == 1
