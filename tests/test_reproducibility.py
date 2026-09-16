"""Determinism: running the harness twice on the same fixtures produces
byte-identical `BenchmarkResult` rows.

If a future change adds time.now() or a random seed to the aggregation
path this test will start failing immediately, which is the point.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.fixtures import load_by_source
from specint.records import SourceQuery


def _run(fixtures_dir: Path) -> str:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_by_source(query, fixtures_dir)
    rows = run_comparison(query, by_source, notes="repro")
    return json.dumps(
        [r.model_dump(mode="json") for r in rows],
        sort_keys=True,
    )


def test_harness_is_byte_deterministic(fixtures_dir: Path) -> None:
    first = _run(fixtures_dir)
    second = _run(fixtures_dir)
    assert first == second


def test_harness_ordering_is_stable(fixtures_dir: Path) -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, load_by_source(query, fixtures_dir), notes="order")
    sources = [r.source for r in rows]
    assert sources[-1] == "__total__"
    assert sources[:-1] == sorted(sources[:-1])
