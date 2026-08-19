from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main


def test_bench_command_writes_json_and_exits_ok(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPECINT_FIXTURE_ROOT", str(Path(__file__).parent / "fixtures"))
    out = tmp_path / "bench.json"
    rc = main(["bench", "--output", str(out), "--terms", "cooking", "recipe"])
    assert rc in (0, 4)
    payload = json.loads(out.read_text())
    assert "runs" in payload and "delta" in payload
    assert set(payload["runs"].keys()) == {"v1", "v2_procedural"}
    assert payload["delta"]["verdict"] in {"dominates", "tie", "dominated", "mixed"}


def test_compare_v2_profile_produces_procedural_metric(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPECINT_FIXTURE_ROOT", str(Path(__file__).parent / "fixtures"))
    out = tmp_path / "cmp.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--profile",
            "v2_procedural",
            "--terms",
            "cooking",
            "recipe",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["scorer_profile"] == "v2_procedural"
    rows = {r["source"]: r for r in payload["rows"]}
    assert "__total__" in rows
    assert rows["__total__"]["scorer_profile"] == "v2_procedural"
    assert rows["__total__"]["mean_procedural_density"] >= 0.0


def test_dedup_report_command(monkeypatch, capsys):
    monkeypatch.setenv("SPECINT_FIXTURE_ROOT", str(Path(__file__).parent / "fixtures"))
    rc = main(["dedup-report"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "n_input" in payload and "n_unique" in payload
    assert payload["n_input"] >= payload["n_unique"]
