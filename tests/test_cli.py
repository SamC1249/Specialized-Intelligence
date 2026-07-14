import json
from pathlib import Path

import pytest

from specint.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert slug in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources


def test_cli_compare_with_fixtures_dir_and_v2_scorer(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--fixtures-dir",
            str(FIXTURES),
            "--scorer",
            "v2",
            "--dedup",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["scorer"] == "v2"
    assert total["n_records"] > 0
    assert total["n_license_clean"] > 0


def test_cli_matrix_fixtures(tmp_path: Path):
    out = tmp_path / "matrix.json"
    rc = main(
        [
            "matrix",
            "--suite",
            str(FIXTURES / "suite/query_suite.json"),
            "--fixtures-dir",
            str(FIXTURES),
            "--scorer",
            "v2",
            "--dedup",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "suite" in payload
    assert "per_query" in payload
    assert "per_source" in payload
    per_source = payload["per_source"]
    assert any(r["source"] == "__total__" for r in per_source)


def test_cli_scorer_compare(tmp_path: Path):
    out = tmp_path / "scorer.json"
    rc = main(
        [
            "scorer-compare",
            "--fixtures-dir",
            str(FIXTURES),
            "--terms",
            "cooking",
            "--dedup",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload["reports"]) == {"v1", "v2"}
    v1_total = next(r for r in payload["reports"]["v1"] if r["source"] == "__total__")
    v2_total = next(r for r in payload["reports"]["v2"] if r["source"] == "__total__")
    assert v1_total["n_license_clean"] == v2_total["n_license_clean"]


def test_cli_diff_command(tmp_path: Path):
    v1 = tmp_path / "v1.json"
    v2 = tmp_path / "v2.json"
    diff = tmp_path / "diff.json"
    main(
        [
            "compare",
            "--fixtures",
            "--fixtures-dir",
            str(FIXTURES),
            "--scorer",
            "v1",
            "--output",
            str(v1),
        ]
    )
    main(
        [
            "compare",
            "--fixtures",
            "--fixtures-dir",
            str(FIXTURES),
            "--scorer",
            "v2",
            "--output",
            str(v2),
        ]
    )
    rc = main(["diff", str(v1), str(v2), "--output", str(diff)])
    assert rc == 0
    payload = json.loads(diff.read_text())
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["baseline_scorer"] == "v1"
    assert total["candidate_scorer"] == "v2"


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_no_output_writes_default(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(
        [
            "compare",
            "--fixtures",
            "--fixtures-dir",
            str(FIXTURES),
            "--scorer",
            "v2",
        ]
    )
    assert rc == 0
    report_files = list((tmp_path / "reports").glob("compare-*.json"))
    assert len(report_files) == 1


def test_cli_unknown_scorer_rejected():
    with pytest.raises(SystemExit):
        main(["compare", "--fixtures", "--scorer", "v99"])
