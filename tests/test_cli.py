import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert slug in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path, capsys):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_ablate_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "ablation.json"
    rc = main(["ablate", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "configs" in payload and "rankings" in payload
    assert "default" in payload["configs"]


def test_cli_dedup_fixtures_reports_groups(tmp_path: Path):
    out = tmp_path / "dedup.json"
    rc = main(["dedup", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "n_groups" in payload and payload["n_records"] >= 0


def test_cli_compare_with_dedup_flag(tmp_path: Path):
    out = tmp_path / "compare-dedup.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--dedup",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    total_row = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total_row["n_records"] >= 0
