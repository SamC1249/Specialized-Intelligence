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


def test_cli_compare_only_restricts_sources(tmp_path: Path):
    out = tmp_path / "only.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--only",
            "wikimedia",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    per_source = {r["source"] for r in payload["rows"] if r["source"] != "__total__"}
    assert per_source == {"wikimedia"}


def test_cli_compare_dedupe_flag_marks_total(tmp_path: Path):
    out = tmp_path / "dedupe.json"
    rc = main(["compare", "--fixtures", "--dedupe", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert "dedupe=on" in total["notes"]
