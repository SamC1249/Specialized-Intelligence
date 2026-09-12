from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl", "youtube_cc"):
        assert slug in out


def test_cli_scorers_lists_registry(capsys):
    rc = main(["scorers"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "v1" in out
    assert "v2" in out


def test_cli_presets_lists_known_presets(capsys):
    rc = main(["presets"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cooking" in out
    assert "cooking_multi" in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path, capsys):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    assert payload["scorer"] == "v1"
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources


def test_cli_compare_with_scorer_v2_and_dedup(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--preset",
            "cooking",
            "--scorer",
            "v2",
            "--dedup",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["scorer"] == "v2"
    assert payload["dedup"] is True
    for row in payload["rows"]:
        assert row["scorer"] == "v2"


def test_cli_compare_preset_multilingual(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--preset",
            "cooking_multi",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "receta" in payload["query"]["terms"]


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2
