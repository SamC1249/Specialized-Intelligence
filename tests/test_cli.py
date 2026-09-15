import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl", "youtube_cc"):
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
    out = tmp_path / "ablate.json"
    rc = main(["ablate", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "profiles" in payload
    assert set(payload["profiles"].keys()) >= {"balanced", "license_first", "procedural_first"}
    for block in payload["profiles"].values():
        assert "ranking" in block
        assert "weights" in block


def test_cli_dedup_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "dedup.json"
    rc = main(["dedup", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["n_input"] == payload["n_unique"] + payload["n_collisions"]
    assert isinstance(payload["collision_matrix"], dict)


def test_cli_compare_accepts_profile(tmp_path: Path):
    out = tmp_path / "compare.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "--profile",
            "procedural_first",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["profile"] == "procedural_first"
