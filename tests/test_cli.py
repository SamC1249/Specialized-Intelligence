import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl", "youtube"):
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
    assert "youtube" in sources
    assert "dedupe" not in payload  # off by default


def test_cli_compare_with_dedupe_flag(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--dedupe", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "dedupe" in payload
    assert "overlap" in payload["dedupe"]


def test_cli_dedupe_subcommand(tmp_path: Path, capsys):
    out = tmp_path / "dedupe.json"
    rc = main(["dedupe", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "n_records" in payload
    assert "n_after_dedupe" in payload
    assert payload["n_after_dedupe"] <= payload["n_records"]
    assert isinstance(payload["overlap"], dict)


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2
