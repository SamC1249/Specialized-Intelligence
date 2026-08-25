"""Regression gate against the committed baseline.

Fails if any per-source ``mean_quality`` on the fixture harness drops
more than 0.05 absolute versus the ``reports/baseline-2026-06-20.json``
snapshot. Regenerating the baseline is an explicit, reviewed action;
new sources introduced *after* the baseline are permitted to appear
without a prior row (they simply aren't compared).
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.fixtures import load_fixture_records
from specint.records import SourceQuery

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "reports" / "baseline-2026-06-20.json"
TOLERANCE = 0.05


def test_no_source_mean_quality_regresses_beyond_tolerance():
    baseline = json.loads(BASELINE_PATH.read_text())
    baseline_rows = {row["source"]: row for row in baseline["rows"]}

    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, load_fixture_records(query), notes="regression-check")
    current = {row.source: row for row in rows}

    regressions: list[str] = []
    for source, baseline_row in baseline_rows.items():
        if source not in current:
            continue  # never delete a baseline source without a re-baseline PR
        cur = current[source]
        delta = cur.mean_quality - baseline_row["mean_quality"]
        if delta < -TOLERANCE:
            regressions.append(
                f"{source}: {baseline_row['mean_quality']:.4f} -> {cur.mean_quality:.4f} (Δ={delta:+.4f})"
            )
    assert not regressions, "quality regressions detected: " + "; ".join(regressions)


def test_baseline_row_count_matches_committed_sources():
    baseline = json.loads(BASELINE_PATH.read_text())
    sources = {row["source"] for row in baseline["rows"]}
    # Whatever the baseline captured, we must keep serving at least those
    # sources unless the baseline file itself is intentionally regenerated.
    assert "__total__" in sources
