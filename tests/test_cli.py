import json
from pathlib import Path

import pytest
from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl", "youtube_cc"):
        assert slug in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources
    # With real fixtures, __total__ must carry a non-zero record count.
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["n_records"] > 0
    assert payload["dedup"] is True
    assert payload["duration_profile"] == "short_form"


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert exc.value.code == 2


def test_cli_ablate_duration_writes_delta(tmp_path: Path):
    out = tmp_path / "ablation.json"
    rc = main(
        [
            "ablate-duration",
            "--fixtures",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload["per_profile"]) == {"short_form", "long_form"}
    assert "delta_long_minus_short" in payload
    assert "__total__" in payload["delta_long_minus_short"]
