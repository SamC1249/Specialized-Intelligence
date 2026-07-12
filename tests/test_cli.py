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


def test_cli_domains_lists_known_domains(capsys):
    rc = main(["domains"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("cooking", "laboratory", "surgery", "sports", "manufacturing"):
        assert slug in out


def test_cli_compare_with_domain_writes_domain_specific_report(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--domain",
            "laboratory",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["domain"] == "laboratory"


def test_cli_ablate_writes_report(tmp_path: Path):
    out = tmp_path / "ablation.json"
    rc = main(["ablate", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["domain"] == "cooking"
    assert "v1" in payload["variants"]
    assert "v2" in payload["variants"]
