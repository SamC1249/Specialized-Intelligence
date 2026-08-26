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

from specint.dedup import deduplicate
from specint.quality import DEFAULT_DURATION_PROFILE, DurationProfile, score_records
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
    n_duplicates_removed: int = 0,
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
        n_duplicates_removed=n_duplicates_removed,
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    dedup: bool = True,
    duration_profile: DurationProfile = DEFAULT_DURATION_PROFILE,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    When ``dedup`` is True (default) the aggregate row's counts are
    computed *after* cross-source deduplication and ``n_duplicates_removed``
    is populated. Per-source rows are always the pre-dedup view so a
    source can never be penalised for another source's mirror.
    """
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, duration_profile=duration_profile)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))

    if dedup:
        dr = deduplicate(all_scored)
        rows.append(
            aggregate(
                "__total__",
                query.terms,
                dr.kept,
                notes=notes,
                n_duplicates_removed=dr.removed,
            )
        )
    else:
        rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))
    return rows
