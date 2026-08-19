"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs
— typically produced by feeding offline fixtures or live `search()`
calls through a scorer profile — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The harness always:
1. Applies the configured scorer profile (default: `v1` for
   back-compat with the seed baseline).
2. Runs cross-source deduplication and reports `n_unique_after_dedup`.
3. Backfills `record.language` via the stoplist detector so
   `languages_seen` isn't empty just because upstream forgot to tag.
4. Computes `mean_procedural_density` even under `v1` so runs are
   directly comparable across profiles.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.quality import (
    backfill_languages,
    dedupe,
    score_procedural_density,
    score_records_with_profile,
)
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
    scorer_profile: str = "v1",
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
    dedup_report = dedupe(items)
    procedural = [score_procedural_density(r) for r in items]
    languages = sorted({r.language for r in items if r.language})

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
        n_unique_after_dedup=dedup_report.n_unique,
        license_clean_ratio=(license_clean / len(items)) if items else 0.0,
        mean_procedural_density=(float(statistics.fmean(procedural)) if procedural else 0.0),
        languages_seen=languages,
        scorer_profile=scorer_profile,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    scorer_profile: str = "v1",
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row."""
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        enriched = backfill_languages(records)
        scored = score_records_with_profile(enriched, scorer_profile)
        all_scored.extend(scored)
        rows.append(
            aggregate(source, query.terms, scored, notes=notes, scorer_profile=scorer_profile)
        )
    rows.append(
        aggregate("__total__", query.terms, all_scored, notes=notes, scorer_profile=scorer_profile)
    )
    return rows
