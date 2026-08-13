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
    assert "overlap" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    total_row = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total_row["n_records"] > 0


def test_cli_compare_dedupe_flag_populates_dedupe_fields(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--dedupe", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["dedupe_enabled"] is True
    total_row = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total_row["n_duplicates"] >= 1
    assert total_row["n_after_dedupe"] < total_row["n_records"]


def test_cli_dedupe_subcommand_emits_overlap(tmp_path: Path):
    out = tmp_path / "overlap.json"
    rc = main(["dedupe", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload["overlap"]["sources"]) == {
        "archive_org",
        "common_crawl",
        "peertube",
        "wikimedia",
    }
    assert payload["total_collapsed"] >= 1


def test_cli_ablate_subcommand_produces_matrix(tmp_path: Path):
    out = tmp_path / "ablate.json"
    rc = main(["ablate", "--fixtures", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    matrix = payload["mean_quality_matrix"]
    assert set(matrix.keys()) == {"baseline", "license_heavy", "procedural_heavy"}
    for _variant, per_source in matrix.items():
        assert "__total__" in per_source
        for mq in per_source.values():
            assert 0.0 <= mq <= 1.0


def test_cli_compare_multilingual_widens_seed_terms(tmp_path: Path):
    out = tmp_path / "ml.json"
    rc = main(["compare", "--fixtures", "--multilingual", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    terms = payload["query"]["terms"]
    assert "cocinar" in terms
    assert "料理" in terms


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2
