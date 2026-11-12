"""Ablation harness tests."""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_ablation
from specint.fixtures import load_fixture_corpus
from specint.quality import list_profiles
from specint.records import SourceQuery


def test_run_ablation_emits_row_per_profile_per_source() -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_fixture_corpus(query)
    rows = run_ablation(query, by_source, notes="ci")

    profiles = list_profiles()
    sources = set(by_source) | {"__total__"}
    pairs = {(row["profile"], row["source"]) for row in rows}

    for p in profiles:
        for s in sources:
            assert (p, s) in pairs, f"missing ablation row for profile={p} source={s}"


def test_run_ablation_serialises_to_json(tmp_path: Path) -> None:
    query = SourceQuery(terms=["cooking"], max_results=10)
    by_source = load_fixture_corpus(query)
    rows = run_ablation(query, by_source)
    out = tmp_path / "ablate.json"
    out.write_text(json.dumps({"rows": rows}))
    reloaded = json.loads(out.read_text())
    assert reloaded["rows"] == rows
