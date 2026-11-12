import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert slug in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    assert payload["profile"] == "v1"
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    # Fixtures must actually drive non-trivial comparison.
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["n_records"] > 0


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_compare_profile_v2_differs_from_v1(tmp_path: Path):
    out_v1 = tmp_path / "v1.json"
    out_v2 = tmp_path / "v2.json"
    assert main(["compare", "--fixtures", "--output", str(out_v1), "--profile", "v1"]) == 0
    assert main(["compare", "--fixtures", "--output", str(out_v2), "--profile", "v2"]) == 0
    v1 = json.loads(out_v1.read_text())
    v2 = json.loads(out_v2.read_text())
    assert v1["profile"] == "v1"
    assert v2["profile"] == "v2"
    v1_total = next(r for r in v1["rows"] if r["source"] == "__total__")
    v2_total = next(r for r in v2["rows"] if r["source"] == "__total__")
    assert v1_total["n_records"] == v2_total["n_records"]
    assert v1_total["mean_quality"] != v2_total["mean_quality"]


def test_cli_ablate_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "ablate.json"
    rc = main(["ablate", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload.get("profiles")
    rows = payload["rows"]
    profiles = {r["profile"] for r in rows}
    assert profiles == set(payload["profiles"])


def test_cli_dedup_fixtures_reports_rate(tmp_path: Path):
    out = tmp_path / "dedup.json"
    rc = main(["dedup", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["input_count"] >= payload["output_count"] >= 0
    assert 0.0 <= payload["dedup_rate"] <= 1.0
