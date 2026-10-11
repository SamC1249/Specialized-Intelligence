"""Systematic comparison harness.

Given a `SourceQuery` and a mapping of `{source_slug: list_of_records}` —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

Per-source rows describe the output of a single adapter in isolation.
The `__total__` row additionally runs cross-source deduplication so
`n_duplicates_dropped` surfaces redundancy between adapters (e.g. a
Wikimedia Commons upload that also lives on the Internet Archive).

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.quality import dedupe_records, score_records
from specint.records import BenchmarkResult, License, SourceQuery, VideoRecord


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    k = max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1))))
    return s[k]


def _top_k_mean(values: list[float], k: int) -> float:
    if not values:
        return 0.0
    top = sorted(values, reverse=True)[:k]
    return float(statistics.fmean(top))


def _median_int(values: list[int]) -> int | None:
    if not values:
        return None
    s = sorted(values)
    mid = s[len(s) // 2]
    return int(mid)


def aggregate(
    source: str,
    query_terms: list[str],
    records: Iterable[VideoRecord],
    notes: str = "",
    n_duplicates_dropped: int = 0,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        return BenchmarkResult.empty(source, query_terms, notes=notes)

    qualities = [r.quality_score or 0.0 for r in items]
    durations = [r.duration_s or 0.0 for r in items]
    heights = [r.height for r in items if r.height]
    license_clean = sum(
        1 for r in items if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    license_clean_seconds = sum(
        (r.duration_s or 0.0)
        for r in items
        if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    authors = {r.author for r in items if r.author}
    with_steps = sum(1 for r in items if r.recipe_steps)

    return BenchmarkResult(
        source=source,
        query_terms=list(query_terms),
        n_records=len(items),
        n_license_clean=license_clean,
        total_duration_s=float(sum(durations)),
        license_clean_hours=round(license_clean_seconds / 3600.0, 6),
        mean_quality=float(statistics.fmean(qualities)) if qualities else 0.0,
        p50_quality=_percentile(qualities, 50),
        p90_quality=_percentile(qualities, 90),
        top10_mean_quality=_top_k_mean(qualities, 10),
        median_height=_median_int([int(h) for h in heights]),
        unique_authors=len(authors),
        n_with_steps=with_steps,
        n_duplicates_dropped=n_duplicates_dropped,
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    The `__total__` row reports post-dedupe metrics so cross-source
    overlap is visible in `n_duplicates_dropped`.
    """
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))

    deduped, stats = dedupe_records(all_scored)
    rows.append(
        aggregate(
            "__total__",
            query.terms,
            deduped,
            notes=notes,
            n_duplicates_dropped=stats.n_duplicates_dropped,
        )
    )
    return rows
