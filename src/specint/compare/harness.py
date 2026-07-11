"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The `__total__` row includes cross-source dedup metrics
(`n_unique_across_sources`, `duplicate_rate`, `unique_duration_s`).
Per-source rows fill the same metrics using in-source dedup so that
identical records from a single upstream (e.g. two fixtures of the same
Wikimedia video) do not inflate the yield.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedup import deduplicate, duplicate_rate, unique_duration_s
from specint.domains import DEFAULT_DOMAIN_SLUG, Domain
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
    unique = deduplicate(items)

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
        n_unique_across_sources=len(unique),
        duplicate_rate=duplicate_rate(items),
        unique_duration_s=unique_duration_s(items),
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    domain: Domain | str | None = None,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    The ``domain`` parameter selects the verb vocabulary used by the
    ``action_density`` quality component. Defaults to ``cooking``.
    """
    dom = domain if domain is not None else DEFAULT_DOMAIN_SLUG
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, dom)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))
    return rows
