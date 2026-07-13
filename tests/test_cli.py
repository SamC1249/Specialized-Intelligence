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


def test_cli_ablate_fixtures_writes_bundle(tmp_path: Path):
    out = tmp_path / "ablation.json"
    rc = main(["ablate", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "presets" in payload
    assert set(payload["presets"]).issuperset({"baseline", "no_license"})


def test_cli_dedup_reads_json_list(tmp_path: Path):
    from datetime import UTC, datetime

    from specint.records import Provenance, VideoRecord

    prov = Provenance(extractor="cli.test", fetched_at=datetime.now(UTC), query="")
    rec_a = VideoRecord(
        id="a:1",
        source="a",
        source_native_id="1",
        url="https://example.test/1",
        title="How to make pasta",
        author="Chef",
        duration_s=300.0,
        provenance=prov,
    )
    rec_b = VideoRecord(
        id="a:2",
        source="a",
        source_native_id="2",
        url="https://example.test/2",
        title="How to make pasta",
        author="Chef",
        duration_s=302.0,
        provenance=prov,
    )
    inp = tmp_path / "records.json"
    inp.write_text(json.dumps([rec_a.model_dump(mode="json"), rec_b.model_dump(mode="json")]))
    out = tmp_path / "dedup.json"
    rc = main(["dedup", "--input", str(inp), "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["n_input"] == 2
    assert payload["n_kept"] == 1
