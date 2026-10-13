"""CI regression gate.

Priority-A deliverable in docs/plan-2026-10-12.md (H4): re-run the
fixture comparison harness and assert each source stays within tolerance
of the committed `reports/baseline-latest.json`. Catches silent quality
rot (a license classifier regression, a scorer re-weight, a parse-bug
that drops records) *before* it merges to main.

Tolerances live in `reports/baseline-latest.tolerance.json` so they are
tunable without a code change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.compare import run_fixture_harness

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = REPO_ROOT / "reports" / "baseline-latest.json"
TOLERANCE = REPO_ROOT / "reports" / "baseline-latest.tolerance.json"


def _load_json(path: Path) -> dict:
    assert path.exists(), f"missing {path}; run `python -m specint compare --fixtures` or the baseline script"
    return json.loads(path.read_text())


def test_fixture_harness_matches_committed_baseline_within_tolerance() -> None:
    baseline = _load_json(BASELINE)
    tol = _load_json(TOLERANCE)
    mean_quality_abs = float(tol["mean_quality_abs"])
    n_license_clean_abs = int(tol["n_license_clean_abs"])
    quality_hours_rel = float(tol["quality_hours_rel"])

    _, rows = run_fixture_harness()
    live_by_source = {r.source: r for r in rows}
    baseline_rows = {row["source"]: row for row in baseline["rows"]}

    # The source universe must not shrink silently.
    assert set(live_by_source).issuperset(baseline_rows), (
        f"regression: baseline has sources {set(baseline_rows) - set(live_by_source)} "
        "that the live harness no longer produces"
    )

    failures: list[str] = []
    for source, baseline_row in baseline_rows.items():
        live = live_by_source[source]
        # n_records must never decrease.
        if live.n_records < baseline_row["n_records"]:
            failures.append(
                f"{source}: n_records {live.n_records} < baseline {baseline_row['n_records']}"
            )
        if abs(live.mean_quality - baseline_row["mean_quality"]) > mean_quality_abs:
            failures.append(
                f"{source}: mean_quality {live.mean_quality:.4f} drifted >|{mean_quality_abs}| from baseline {baseline_row['mean_quality']:.4f}"
            )
        if (baseline_row["n_license_clean"] - live.n_license_clean) > n_license_clean_abs:
            failures.append(
                f"{source}: n_license_clean {live.n_license_clean} dropped by more than {n_license_clean_abs} vs baseline {baseline_row['n_license_clean']}"
            )
        baseline_q_hours = float(baseline_row.get("quality_hours", 0.0))
        if baseline_q_hours > 0.0:
            drift = abs(live.quality_hours - baseline_q_hours) / baseline_q_hours
            if drift > quality_hours_rel:
                failures.append(
                    f"{source}: quality_hours {live.quality_hours:.4f} drifted {drift:.2%} > {quality_hours_rel:.0%} from baseline {baseline_q_hours:.4f}"
                )

    assert not failures, "regression(s) vs committed baseline:\n  - " + "\n  - ".join(failures)


@pytest.mark.parametrize("field", ["mean_quality", "n_license_clean", "n_records", "quality_hours"])
def test_baseline_rows_have_all_tracked_fields(field: str) -> None:
    baseline = _load_json(BASELINE)
    for row in baseline["rows"]:
        assert field in row, f"baseline row {row['source']} missing {field}"
