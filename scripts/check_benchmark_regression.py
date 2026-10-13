"""Compare a benchmark report against the committed baseline and fail on drift.

Usage:
    python scripts/check_benchmark_regression.py \
        --candidate reports/compare-fixture.json \
        --baseline reports/baseline-2026-06-20.json

Exit codes:
    0 — all checks passed (or `--update-baseline` wrote a new baseline)
    1 — at least one source regressed beyond tolerance
    2 — baseline is missing a source present in the candidate (soft warn
        is default; set `--strict-new-sources` to fail)
    3 — candidate is missing a source present in the baseline (always fail)
    4 — malformed input

What is checked (per per-source row; `__total__` is checked too but
counts are allowed to grow if a new source arrived):

    - n_records              → must equal baseline exactly
    - n_license_clean        → must equal baseline exactly
    - unique_authors         → must equal baseline exactly
    - total_duration_s       → within --tolerance-duration (default 1e-6)
    - mean_quality           → within --tolerance-quality (default 1e-3)
    - p50_quality            → within --tolerance-quality
    - p90_quality            → within --tolerance-quality

The `notes` field is intentionally ignored (CI runs will use a different
note from the one baked into the baseline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO_ROOT / "reports" / "baseline-2026-06-20.json"
DEFAULT_CANDIDATE = REPO_ROOT / "reports" / "compare-fixture.json"

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_NEW_SOURCE_STRICT = 2
EXIT_MISSING_SOURCE = 3
EXIT_MALFORMED = 4

INT_FIELDS = ("n_records", "n_license_clean", "unique_authors")
FLOAT_DURATION_FIELDS = ("total_duration_s",)
FLOAT_QUALITY_FIELDS = ("mean_quality", "p50_quality", "p90_quality")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        raise SystemExit(EXIT_MALFORMED) from None
    except json.JSONDecodeError as exc:
        print(f"error: malformed JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_MALFORMED) from None


def _rows_by_source(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SystemExit(EXIT_MALFORMED)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or "source" not in row:
            raise SystemExit(EXIT_MALFORMED)
        out[row["source"]] = row
    return out


def _check_row(
    source: str,
    baseline_row: dict[str, Any],
    candidate_row: dict[str, Any],
    tolerance_duration: float,
    tolerance_quality: float,
) -> list[str]:
    problems: list[str] = []
    for field in INT_FIELDS:
        b = baseline_row.get(field, 0)
        c = candidate_row.get(field, 0)
        if int(b) != int(c):
            problems.append(f"{source}.{field}: baseline={b} candidate={c} (exact match required)")
    for field in FLOAT_DURATION_FIELDS:
        b = float(baseline_row.get(field, 0.0))
        c = float(candidate_row.get(field, 0.0))
        if abs(b - c) > tolerance_duration:
            problems.append(
                f"{source}.{field}: baseline={b} candidate={c} "
                f"delta={c - b:+.6f} tol={tolerance_duration}"
            )
    for field in FLOAT_QUALITY_FIELDS:
        b = float(baseline_row.get(field, 0.0))
        c = float(candidate_row.get(field, 0.0))
        if abs(b - c) > tolerance_quality:
            problems.append(
                f"{source}.{field}: baseline={b:.6f} candidate={c:.6f} "
                f"delta={c - b:+.6f} tol={tolerance_quality}"
            )
    return problems


def compare(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    tolerance_duration: float = 1e-6,
    tolerance_quality: float = 1e-3,
    strict_new_sources: bool = False,
) -> tuple[int, list[str]]:
    """Return (exit_code, messages). messages are human-readable."""
    b_rows = _rows_by_source(baseline)
    c_rows = _rows_by_source(candidate)

    messages: list[str] = []
    missing = sorted(set(b_rows) - set(c_rows))
    extras = sorted(set(c_rows) - set(b_rows))

    if missing:
        for src in missing:
            messages.append(f"MISSING: candidate has no row for source={src!r} (regression)")
        return EXIT_MISSING_SOURCE, messages

    problems: list[str] = []
    for src in sorted(b_rows):
        problems.extend(
            _check_row(
                src,
                b_rows[src],
                c_rows[src],
                tolerance_duration=tolerance_duration,
                tolerance_quality=tolerance_quality,
            )
        )

    if problems:
        messages.extend(problems)
        return EXIT_REGRESSION, messages

    if extras:
        for src in extras:
            messages.append(
                f"NEW SOURCE: candidate has new row for source={src!r} (not in baseline)"
            )
        if strict_new_sources:
            return EXIT_NEW_SOURCE_STRICT, messages

    messages.append(f"ok: {len(b_rows)} rows match baseline within tolerance")
    return EXIT_OK, messages


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    p.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    p.add_argument("--tolerance-duration", type=float, default=1e-6)
    p.add_argument("--tolerance-quality", type=float, default=1e-3)
    p.add_argument(
        "--strict-new-sources",
        action="store_true",
        help="fail if candidate has a source not in baseline (default: warn)",
    )
    p.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the baseline file to match the candidate (use inside a PR only)",
    )
    args = p.parse_args(argv)

    candidate = _load(args.candidate)
    baseline = _load(args.baseline)

    if args.update_baseline:
        args.baseline.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n")
        print(f"updated baseline: {args.baseline}", file=sys.stderr)
        return EXIT_OK

    exit_code, messages = compare(
        candidate=candidate,
        baseline=baseline,
        tolerance_duration=args.tolerance_duration,
        tolerance_quality=args.tolerance_quality,
        strict_new_sources=args.strict_new_sources,
    )
    for msg in messages:
        prefix = "ok" if exit_code == EXIT_OK else "fail"
        print(f"[{prefix}] {msg}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
