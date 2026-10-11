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
    total = next(row for row in payload["rows"] if row["source"] == "__total__")
    assert total["n_records"] > 0  # fixtures mode now loads real sample data
    assert "license_clean_hours" in total


def test_cli_compare_language_flag_selects_seed_terms(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--language", "ja", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["query"]["language"] == "ja"
    assert any("レシピ" in t for t in payload["query"]["terms"])


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_languages_prints_registry(capsys):
    rc = main(["languages"])
    assert rc == 0
    out = capsys.readouterr().out
    for tag in ("en", "es", "ja", "zh"):
        assert tag in out


def test_cli_diff_reports_deltas(tmp_path: Path):
    base = tmp_path / "base.json"
    new = tmp_path / "new.json"
    rc = main(["compare", "--fixtures", "--language", "en", "--output", str(base)])
    assert rc == 0
    rc = main(["compare", "--fixtures", "--language", "en", "--output", str(new)])
    assert rc == 0
    rc = main(["diff", str(base), str(new), "--output", str(tmp_path / "d.json")])
    assert rc == 0
    diff = json.loads((tmp_path / "d.json").read_text())
    assert "diffs" in diff and len(diff["diffs"]) > 0
    total = next(row for row in diff["diffs"] if row["source"] == "__total__")
    assert total["n_records"]["delta"] == 0  # same report, no delta
