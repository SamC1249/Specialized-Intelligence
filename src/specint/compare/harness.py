"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs
— typically produced by feeding offline fixtures or live `search()`
calls through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

Additions since seed:
  * `profile`      — named scoring profile (`baseline` | `cooking` | …).
                     Default: `baseline`, so existing reports keep
                     validating.
  * `deduplicate`  — collapse duplicates across sources with
                     `quality.dedup.deduplicate`. Default: False, again
                     for backwards compat with the seed baseline.

Both `n_duplicates_dropped` and `n_relevance_clean` are surfaced in the
`notes` field so callers that persisted the frozen
`BenchmarkResult` schema can still round-trip old reports.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable, Mapping

from specint.quality import deduplicate, is_cooking_relevant, score_records
from specint.records import BenchmarkResult, License, SourceQuery, VideoRecord


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    k = max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1))))
    return s[k]


def _augment_notes(base_notes: str, extras: dict[str, int]) -> str:
    if not any(extras.values()):
        return base_notes
    encoded = json.dumps(extras, sort_keys=True)
    if not base_notes:
        return encoded
    return f"{base_notes} :: {encoded}"


def aggregate(
    source: str,
    query_terms: list[str],
    records: Iterable[VideoRecord],
    notes: str = "",
    *,
    n_duplicates_dropped: int = 0,
    n_relevance_clean: int | None = None,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        return BenchmarkResult.empty(
            source,
            query_terms,
            notes=_augment_notes(
                notes,
                {
                    "n_duplicates_dropped": n_duplicates_dropped,
                    "n_relevance_clean": n_relevance_clean or 0,
                },
            ),
        )

    qualities = [r.quality_score or 0.0 for r in items]
    durations = [r.duration_s or 0.0 for r in items]
    license_clean = sum(
        1 for r in items if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    authors = {r.author for r in items if r.author}
    relevance_clean = (
        n_relevance_clean
        if n_relevance_clean is not None
        else sum(1 for r in items if is_cooking_relevant(r))
    )

    return BenchmarkResult(
        source=source,
        query_terms=list(query_terms),
        n_records=len(items),
        n_license_clean=license_clean,
        total_duration_s=float(sum(durations)),
        mean_quality=float(statistics.fmean(qualities)),
        p50_quality=_percentile(qualities, 50),
        p90_quality=_percentile(qualities, 90),
        unique_authors=len(authors),
        notes=_augment_notes(
            notes,
            {
                "n_duplicates_dropped": n_duplicates_dropped,
                "n_relevance_clean": relevance_clean,
            },
        ),
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    *,
    profile: str = "baseline",
    deduplicate_across_sources: bool = False,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row."""
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, profile=profile)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))

    total_dedup_dropped = 0
    if deduplicate_across_sources and all_scored:
        result = deduplicate(all_scored)
        total_dedup_dropped = result.n_dropped
        all_scored = result.kept

    rows.append(
        aggregate(
            "__total__",
            query.terms,
            all_scored,
            notes=notes,
            n_duplicates_dropped=total_dedup_dropped,
        )
    )
    return rows
