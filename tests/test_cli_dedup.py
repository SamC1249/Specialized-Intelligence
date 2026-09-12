import json
from pathlib import Path

from specint.cli import main


def test_cli_dedup_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "dedup.json"
    rc = main(["dedup", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    assert {"wikimedia", "archive_org", "peertube", "common_crawl"} <= sources
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["n_records"] >= total["n_unique"] > 0
    assert total["n_duplicates"] >= 1


def test_cli_dedup_refuses_without_fixtures(tmp_path: Path):
    rc = main(["dedup"])
    assert rc == 2


def test_cli_check_invariants_reports_clean(capsys):
    rc = main(["check-invariants"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["n_violations"] == 0
