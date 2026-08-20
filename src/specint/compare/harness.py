"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedup import dedup_records
from specint.quality import score_records
from specint.records import BenchmarkResult, License, SourceQuery, VideoRecord


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    k = max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1))))
    return s[k]


def aggregate(
    source: str,
    query_terms: list[str],
    records: Iterable[VideoRecord],
    notes: str = "",
) -> BenchmarkResult:
    items = list(records)
    if not items:
        return BenchmarkResult.empty(source, query_terms, notes=notes)

    qualities = [r.quality_score or 0.0 for r in items]
    durations = [r.duration_s or 0.0 for r in items]
    license_clean = sum(
        1 for r in items if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    authors = {r.author for r in items if r.author}

    return BenchmarkResult(
        source=source,
        query_terms=list(query_terms),
        n_records=len(items),
        n_license_clean=license_clean,
        total_duration_s=float(sum(durations)),
        mean_quality=float(statistics.fmean(qualities)) if qualities else 0.0,
        p50_quality=_percentile(qualities, 50),
        p90_quality=_percentile(qualities, 90),
        unique_authors=len(authors),
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append `__total__` +
    `__total_after_dedup__` rows.

    Cross-source metadata dedup is applied *after* per-source aggregation,
    so per-source `n_records` reflects gross ingest yield and the two
    total rows expose the effect of dedup on the pooled corpus.
    """
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))

    dedup_result = dedup_records(all_scored)
    dedup_notes = (
        f"{notes};dedup_removed={dedup_result.n_duplicates_removed}"
        if notes
        else f"dedup_removed={dedup_result.n_duplicates_removed}"
    )
    rows.append(
        aggregate("__total_after_dedup__", query.terms, dedup_result.kept, notes=dedup_notes)
    )
    return rows
