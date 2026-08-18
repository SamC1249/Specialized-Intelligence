import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in (
        "wikimedia",
        "wikimedia_category",
        "archive_org",
        "peertube",
        "common_crawl",
    ):
        assert slug in out


def test_cli_profiles_lists_weight_profiles(capsys):
    rc = main(["profiles"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in ("default", "procedural", "resolution"):
        assert name in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload  # single-profile mode also emits `rows`
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    assert "__unique_total__" in sources


def test_cli_compare_all_profiles_emits_per_profile_rows(tmp_path: Path):
    out = tmp_path / "report-all.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "--profile",
            "all",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload["profiles"]) >= {"default", "procedural", "resolution"}


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2
