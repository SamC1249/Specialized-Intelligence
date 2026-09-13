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


def test_cli_policies_lists_registered(capsys):
    rc = main(["policies"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in ("baseline", "procedural-heavy", "license-strict"):
        assert name in out


def test_cli_sweep_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "sweep.json"
    rc = main(["sweep", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload) >= {"meta", "policies", "rows", "frontier", "dedup"}
    assert payload["meta"]["query"]["terms"] == ["cooking"]


def test_cli_sweep_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["sweep", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_sweep_rejects_unknown_policy(tmp_path: Path):
    rc = main(
        [
            "sweep",
            "--fixtures",
            "--policies",
            "no-such-policy",
            "--output",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 2
