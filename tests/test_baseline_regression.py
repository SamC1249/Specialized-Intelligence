"""Baseline regression gate.

Turns "someone silently made mean_quality worse" into a red CI build.

We load the *newest* checked-in `reports/baseline-*.json`, re-run the
comparison harness against the same fixtures, and assert per-source
`mean_quality` matches within a small tolerance. If a coding change
legitimately shifts the score (new weights, new component), the
convention is to:

  1. Ship the code change.
  2. Regenerate the baseline via `python scripts/regen_baseline.py`.
  3. Commit the new `reports/baseline-YYYY-MM-DD.json` alongside the code.

This forces every score-changing PR to explicitly commit its new number.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.regen_baseline import build_by_source
from specint.compare import run_comparison
from specint.records import SourceQuery

REPORTS = Path(__file__).resolve().parents[1] / "reports"
TOLERANCE = 1e-6  # exact reproducibility; fixtures are hand-authored, no RNG.


def _newest_baseline() -> Path:
    baselines = sorted(REPORTS.glob("baseline-*.json"))
    assert baselines, "no baseline reports/baseline-*.json checked in"
    return baselines[-1]


def _rerun_current() -> list[dict]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    rows = run_comparison(query, build_by_source(query), notes="fixture-baseline")
    return [r.model_dump(mode="json") for r in rows]


def test_baseline_report_is_reproducible():
    baseline = json.loads(_newest_baseline().read_text())
    current_rows = _rerun_current()
    by_source_baseline = {r["source"]: r for r in baseline["rows"]}
    by_source_current = {r["source"]: r for r in current_rows}
    assert set(by_source_current) == set(by_source_baseline), (
        f"row set drift: current={sorted(by_source_current)} "
        f"vs baseline={sorted(by_source_baseline)}"
    )
    for source, row in by_source_current.items():
        b = by_source_baseline[source]
        for key in ("mean_quality", "p50_quality", "p90_quality"):
            assert row[key] == pytest.approx(b[key], abs=TOLERANCE), (
                f"{source}.{key}: current={row[key]} vs baseline={b[key]}"
            )
        assert row["n_records"] == b["n_records"], source
        assert row["n_license_clean"] == b["n_license_clean"], source


def test_wikimedia_remains_top_ranked():
    """Design invariant: Commons should dominate on our fixture corpus.

    If this ever fails, either (a) we improved a competing source
    materially (celebrate + revisit the priority ordering in AGENTS.md),
    or (b) we regressed the Commons parser (fix it).
    """
    rows = _rerun_current()
    per_source = {r["source"]: r["mean_quality"] for r in rows if not r["source"].startswith("__")}
    top = max(per_source, key=per_source.get)
    assert top == "wikimedia", f"expected wikimedia to top-rank, got {top}: {per_source}"


def test_deduped_row_never_exceeds_total():
    rows = {r["source"]: r for r in _rerun_current()}
    assert rows["__deduped__"]["n_records"] <= rows["__total__"]["n_records"]
    assert rows["__deduped__"]["total_duration_s"] <= rows["__total__"]["total_duration_s"]
