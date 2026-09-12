"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs
— typically produced by feeding offline fixtures or live `search()`
calls — the harness:

  1. Scores every record with the selected scorer (default `v1`).
  2. Optionally deduplicates records **across** sources (see
     `specint.dedup`); the winner for each duplicate cluster keeps its
     source assignment.
  3. Aggregates per-source and emits an aggregate `__total__` row.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

Every `BenchmarkResult` row includes the scorer name so reports stay
comparable across days when the default scorer changes.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedup import deduplicate
from specint.quality import BATCH_SCORERS
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
    scorer: str = "v1",
    n_duplicates_removed: int = 0,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        empty = BenchmarkResult.empty(source, query_terms, notes=notes, scorer=scorer)
        return empty.model_copy(update={"n_duplicates_removed": n_duplicates_removed})

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
        scorer=scorer,
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    scorer: str = "v1",
    dedup: bool = False,
) -> list[BenchmarkResult]:
    """Score, optionally deduplicate, aggregate per source, and add `__total__`."""
    if scorer not in BATCH_SCORERS:
        raise KeyError(f"unknown scorer {scorer!r}; available: {sorted(BATCH_SCORERS)}")
    batch_score = BATCH_SCORERS[scorer]

    scored_by_source: dict[str, list[VideoRecord]] = {
        src: batch_score(records) for src, records in by_source.items()
    }

    removed_by_source: dict[str, int] = dict.fromkeys(scored_by_source, 0)
    if dedup:
        all_records: list[VideoRecord] = []
        for records in scored_by_source.values():
            all_records.extend(records)
        result = deduplicate(all_records)
        kept_ids = {r.id for r in result.kept}
        new_by_source: dict[str, list[VideoRecord]] = {src: [] for src in scored_by_source}
        for src, records in scored_by_source.items():
            for r in records:
                if r.id in kept_ids:
                    new_by_source[src].append(r)
                else:
                    removed_by_source[src] += 1
        scored_by_source = new_by_source

    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    total_removed = 0
    for source in sorted(scored_by_source):
        records = scored_by_source[source]
        all_scored.extend(records)
        removed = removed_by_source.get(source, 0)
        total_removed += removed
        rows.append(
            aggregate(
                source,
                query.terms,
                records,
                notes=notes,
                scorer=scorer,
                n_duplicates_removed=removed,
            )
        )
    rows.append(
        aggregate(
            "__total__",
            query.terms,
            all_scored,
            notes=notes,
            scorer=scorer,
            n_duplicates_removed=total_removed,
        )
    )
    return rows
