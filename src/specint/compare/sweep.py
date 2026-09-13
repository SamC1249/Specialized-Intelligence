"""Policy sweep: run the comparison harness under every named policy.

Emits a JSON-serialisable payload with:
  - `policies`  : ordered list of policy names that ran.
  - `rows`      : one BenchmarkResult-per-(policy, source) plus a
                  `__total__` row per policy.
  - `frontier`  : subset of per-policy `__total__` rows that lie on the
                  Pareto frontier of (mean_quality, n_license_clean).
  - `dedup`     : DedupReport computed once over the union of records.
  - `meta`      : query, notes, timestamp.

The sweep is deterministic given the input `by_source` mapping.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from specint.compare.dedup import DedupReport, build_report
from specint.compare.harness import aggregate
from specint.quality import POLICIES, QualityPolicy, score_records
from specint.records import BenchmarkResult, SourceQuery, VideoRecord, utcnow


def _pareto_frontier(rows: list[BenchmarkResult]) -> list[BenchmarkResult]:
    """Non-dominated rows on (mean_quality UP, n_license_clean UP).

    We use total rows only (one per policy). A row R is dominated iff
    another row has >= mean_quality and >= n_license_clean with strict
    inequality on at least one axis.
    """

    frontier: list[BenchmarkResult] = []
    for r in rows:
        dominated = False
        for other in rows:
            if other is r:
                continue
            better_q = other.mean_quality >= r.mean_quality
            better_lc = other.n_license_clean >= r.n_license_clean
            strictly = (
                other.mean_quality > r.mean_quality or other.n_license_clean > r.n_license_clean
            )
            if better_q and better_lc and strictly:
                dominated = True
                break
        if not dominated:
            frontier.append(r)
    return frontier


def run_sweep(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    policies: Mapping[str, QualityPolicy] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    policy_map = dict(policies) if policies is not None else dict(POLICIES)

    all_rows: list[dict[str, Any]] = []
    total_rows_by_policy: dict[str, BenchmarkResult] = {}

    for policy_name in sorted(policy_map):
        policy = policy_map[policy_name]
        scored_by_source: dict[str, list[VideoRecord]] = {}
        for source, records in sorted(by_source.items()):
            scored_by_source[source] = score_records(records, policy=policy)

        per_source_rows: list[BenchmarkResult] = []
        combined: list[VideoRecord] = []
        for source, scored in scored_by_source.items():
            combined.extend(scored)
            row = aggregate(source, query.terms, scored, notes=notes or policy_name)
            per_source_rows.append(row)

        total_row = aggregate("__total__", query.terms, combined, notes=notes or policy_name)
        total_rows_by_policy[policy_name] = total_row

        for row in [*per_source_rows, total_row]:
            payload = row.model_dump(mode="json")
            payload["policy"] = policy_name
            all_rows.append(payload)

    frontier_rows = _pareto_frontier(list(total_rows_by_policy.values()))
    frontier_payload: list[dict[str, Any]] = []
    for row in frontier_rows:
        for name, tr in total_rows_by_policy.items():
            if tr is row:
                payload = row.model_dump(mode="json")
                payload["policy"] = name
                frontier_payload.append(payload)
                break
    frontier_payload.sort(key=lambda r: r["policy"])

    dedup_report: DedupReport = build_report([r for records in by_source.values() for r in records])

    procedural_medians: dict[str, float] = {}
    for policy_name, policy in policy_map.items():
        flat: list[VideoRecord] = []
        for records in by_source.values():
            flat.extend(score_records(records, policy=policy))
        quals = [r.quality_score or 0.0 for r in flat]
        procedural_medians[policy_name] = float(statistics.median(quals)) if quals else 0.0

    return {
        "meta": {
            "generated_at": _isoformat(utcnow()),
            "query": query.model_dump(mode="json"),
            "notes": notes,
            "policies": sorted(policy_map),
        },
        "policies": sorted(policy_map),
        "rows": all_rows,
        "frontier": frontier_payload,
        "dedup": dedup_report.as_dict(),
        "policy_quality_p50": procedural_medians,
    }


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
