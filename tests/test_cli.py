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
    assert payload["profiles"] == ["baseline"]
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    for row in payload["rows"]:
        assert row["profile"] == "baseline"
        assert row["n_unique_after_dedupe"] is not None


def test_cli_compare_profile_all_emits_each_profile(tmp_path: Path):
    out = tmp_path / "all.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--profile",
            "all",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    profiles_seen = {row["profile"] for row in payload["rows"]}
    assert "baseline" in profiles_seen
    assert "v2" in profiles_seen


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_dedupe_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "dedupe.json"
    rc = main(["dedupe", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "cross_source" in payload
    assert payload["cross_source"]["n_records"] >= 1


def test_cli_yield_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "yield.json"
    rc = main(["yield", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["estimates"], "yield estimates were empty"
    sources_seen = {row["source"] for row in payload["estimates"]}
    assert {"wikimedia", "archive_org", "peertube", "common_crawl"} <= sources_seen
