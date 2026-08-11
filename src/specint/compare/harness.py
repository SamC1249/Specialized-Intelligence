"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__` row.

The `__total__` row additionally reports:
  - `n_after_dedup`: distinct records after cross-source dedup.
  - `cross_source_duplicates`: number of collapsed groups touching >= 2
    sources.
  - `mean_language_confidence`: metadata-only detector confidence
    aggregated across all records (0..1).

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.compare.dedup import dedupe
from specint.quality import batch_language_confidence, score_records
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
    include_dedup: bool = False,
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

    lang_confidences = batch_language_confidence(items)
    mean_lang = float(statistics.fmean(lang_confidences)) if lang_confidences else 0.0

    n_after_dedup: int | None = None
    cross_source_duplicates: int | None = None
    if include_dedup:
        dr = dedupe(items)
        n_after_dedup = dr.n_output
        cross_source_duplicates = dr.cross_source_duplicates

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
        n_after_dedup=n_after_dedup,
        cross_source_duplicates=cross_source_duplicates,
        mean_language_confidence=mean_lang,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    weights: Mapping[str, float] | None = None,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    `weights` (optional): override the quality-weight vector. When None,
    the default `WEIGHTS` from `specint.quality.metrics` are used.
    """
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, weights=weights)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes, include_dedup=False))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes, include_dedup=True))
    return rows
