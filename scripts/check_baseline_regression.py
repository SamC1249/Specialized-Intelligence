#!/usr/bin/env python3
"""Baseline-regression gate.

Re-runs the comparison harness against the committed fixture suite under
``tests/fixtures/`` and diffs the per-source aggregates against a
committed baseline JSON file. Exits non-zero on regression.

Default baseline: ``reports/baseline-2026-06-20.json`` (the first
baseline shipped with the bootstrap PR).

Rules enforced (per source, excluding ``__total__``):

* ``n_license_clean`` must NEVER shrink. A new filter that drops
  license-clean records is almost always wrong (we want *more* clean
  records, not fewer). To intentionally lower this number (e.g. we
  discover a source has been mis-classified), update the baseline file
  in the same PR with a dedicated commit so the drop is reviewable.
* ``mean_quality`` may drop by at most ``--quality-tolerance`` (default
  0.02, i.e. 2 percentage points on a 0..1 scale). A larger drop
  requires either an updated baseline or ``--allow-quality-regression``.
* ``n_records`` is informational only (new fixtures may add records).

Usage::

    python scripts/check_baseline_regression.py
    python scripts/check_baseline_regression.py --baseline reports/baseline-2026-06-20.json
    python scripts/check_baseline_regression.py --allow-quality-regression

This is wired into ``.github/workflows/ci.yml`` and is also runnable
locally.

Note: the ``python -m specint compare --fixtures`` CLI path is currently
broken (it writes empty record lists for every source; see
``docs/plan-2026-11-12.md`` defect D2). This script therefore drives
the fixture-loading from Python directly so the gate remains honest
until the CLI is fixed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources import REGISTRY
from specint.sources.common_crawl import CommonCrawlRecipeSource

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO_ROOT / "reports" / "baseline-2026-06-20.json"
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"


FixtureLoader = Callable[[Path], Any]


def _load_common_crawl(path: Path) -> dict[str, str]:
    return {
        "html": path.read_text(),
        "url": "https://example.test/recipes/baseline-fixture",
    }


FIXTURE_MAP: dict[str, tuple[str, FixtureLoader]] = {
    "wikimedia": ("wikimedia/search_pasta.json", lambda p: json.loads(p.read_text())),
    "archive_org": ("archive_org/search_cooking.json", lambda p: json.loads(p.read_text())),
    "peertube": ("peertube/search_cooking.json", lambda p: json.loads(p.read_text())),
    "common_crawl": ("common_crawl/recipe_page.html", _load_common_crawl),
}


def _load_fixtures(query: SourceQuery) -> dict[str, list]:
    by_source: dict[str, list] = {}
    for slug, cls in REGISTRY.items():
        if slug not in FIXTURE_MAP:
            raise SystemExit(
                f"registered source {slug!r} has no fixture entry in "
                f"scripts/check_baseline_regression.py::FIXTURE_MAP"
            )
        rel, loader = FIXTURE_MAP[slug]
        raw = loader(FIXTURES_ROOT / rel)
        by_source[slug] = cls().parse(raw, query)
    return by_source


def _current_rows(terms: list[str]) -> dict[str, dict[str, Any]]:
    query = SourceQuery(terms=terms, max_results=25)
    by_source = _load_fixtures(query)
    rows = run_comparison(query, by_source, notes="baseline-regression-gate")
    return {r.source: r.model_dump(mode="json") for r in rows}


def _baseline_rows(baseline_path: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    payload = json.loads(baseline_path.read_text())
    rows = {row["source"]: row for row in payload["rows"]}
    terms = payload["query"]["terms"]
    return terms, rows


def check(
    baseline_path: Path,
    allow_quality_regression: bool,
    quality_tolerance: float,
) -> list[str]:
    if not baseline_path.exists():
        return [f"baseline file not found: {baseline_path}"]
    terms, baseline = _baseline_rows(baseline_path)
    current = _current_rows(terms)

    violations: list[str] = []

    baseline_sources = {s for s in baseline if s != "__total__"}
    current_sources = {s for s in current if s != "__total__"}

    for missing in sorted(baseline_sources - current_sources):
        violations.append(
            f"[{missing}] source present in baseline but missing from current run — "
            "did an adapter get dropped from REGISTRY?"
        )

    for source in sorted(baseline_sources & current_sources):
        b = baseline[source]
        c = current[source]

        b_clean = int(b["n_license_clean"])
        c_clean = int(c["n_license_clean"])
        if c_clean < b_clean:
            violations.append(
                f"[{source}] n_license_clean regressed: {b_clean} -> {c_clean}. "
                "To intentionally lower this, update the baseline JSON in a "
                "dedicated commit."
            )

        b_mq = float(b["mean_quality"])
        c_mq = float(c["mean_quality"])
        drop = b_mq - c_mq
        if drop > quality_tolerance and not allow_quality_regression:
            violations.append(
                f"[{source}] mean_quality regressed by {drop:.4f} "
                f"({b_mq:.4f} -> {c_mq:.4f}), tolerance={quality_tolerance:.4f}. "
                "Rerun with --allow-quality-regression if intentional "
                "(e.g. a stricter scorer)."
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--allow-quality-regression",
        action="store_true",
        help="allow mean_quality to drop beyond --quality-tolerance",
    )
    parser.add_argument("--quality-tolerance", type=float, default=0.02)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print current per-source aggregates on success",
    )
    args = parser.parse_args(argv)

    # Keep CommonCrawlRecipeSource import alive even if tooling marks it
    # as unused; this is the one source most likely to be dropped from
    # REGISTRY by a bad rebase (see defect D9).
    _ = CommonCrawlRecipeSource

    violations = check(
        baseline_path=args.baseline,
        allow_quality_regression=args.allow_quality_regression,
        quality_tolerance=args.quality_tolerance,
    )

    if violations:
        print("baseline-regression-gate: FAIL", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print("baseline-regression-gate: OK")
    if args.verbose:
        rows = _current_rows(_baseline_rows(args.baseline)[0])
        for source in sorted(rows):
            r = rows[source]
            print(
                f"  {source:<14} n={r['n_records']:>3} "
                f"clean={r['n_license_clean']:>3} "
                f"mean_q={r['mean_quality']:.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
