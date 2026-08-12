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


def test_cli_compare_fixtures_actually_parses_records(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["n_records"] > 0, (
        "--fixtures must produce non-empty counts; if this fails, the CLI is "
        "back to the stub-zero behaviour that hides broken adapters in CI."
    )
    assert total["n_license_clean"] > 0
    non_total = [r for r in payload["rows"] if r["source"] != "__total__"]
    non_empty_sources = {r["source"] for r in non_total if r["n_records"] > 0}
    assert len(non_empty_sources) >= 3, f"expected ≥3 non-empty sources, got {non_empty_sources}"


def test_cli_compare_fixtures_dir_flag(tmp_path: Path):
    rc = main(
        [
            "compare",
            "--fixtures",
            "--fixtures-dir",
            str(tmp_path / "does-not-exist"),
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2
