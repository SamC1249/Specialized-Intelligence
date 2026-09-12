"""Deduplication comparison harness.

Runs `dedup_records` per source (plus an aggregate `__total__` row) and
emits a JSON-serialisable payload for `reports/dedup-YYYY-MM-DD.json`.

Separate module from `harness.py` on purpose: the quality-comparison
report is stable across releases; dedup metrics are still being iterated
on (Phase 1 today, phash Phase 2 next).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specint.quality.dedup import DedupResult, aggregate_dedup, dedup_records
from specint.records import SourceQuery, VideoRecord


def run_dedup(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    *,
    notes: str = "",
) -> list[DedupResult]:
    rows: list[DedupResult] = []
    for source, records in sorted(by_source.items()):
        rows.append(dedup_records(records, source))
    rows.append(aggregate_dedup(rows, name="__total__"))
    _ = query, notes
    return rows


def dedup_report_payload(
    query: SourceQuery,
    rows: list[DedupResult],
    *,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "query": query.model_dump(mode="json"),
        "notes": notes,
        "rows": [r.to_dict() for r in rows],
    }
