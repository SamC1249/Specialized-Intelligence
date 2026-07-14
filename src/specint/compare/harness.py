"""Systematic comparison harness.

Given a `SourceQuery` (or a `SourceQuerySuite`) and a set of
(source_slug, list_of_records) pairs — typically produced by feeding
offline fixtures or live `search()` calls through the selected quality
scorer — emit a deterministic list of `BenchmarkResult` rows: one per
source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

New in 2026-07-14:
- `scorer` parameter selects the named quality scorer from
  `specint.quality.registry.SCORERS`. Defaults to `v1` for backwards
  compatibility with the seed baseline.
- `dedup` parameter turns on the cross-source dedup step and tracks
  `n_duplicates` on each `BenchmarkResult`.
- `run_matrix` runs a `SourceQuerySuite` (multiple queries) and
  returns per-(query, source) rows plus a per-source aggregate.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Iterable, Mapping

from specint.compare.dedup import dedupe_records
from specint.quality.registry import DEFAULT_SCORER, get_scorer
from specint.records import (
    BenchmarkResult,
    License,
    SourceQuery,
    SourceQuerySuite,
    VideoRecord,
)


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
    scorer: str = DEFAULT_SCORER,
    n_duplicates: int = 0,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        empty = BenchmarkResult.empty(source, query_terms, notes=notes, scorer=scorer)
        return empty.model_copy(update={"n_duplicates": n_duplicates})

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
        n_duplicates=n_duplicates,
        scorer=scorer,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    scorer: str = DEFAULT_SCORER,
    dedup: bool = False,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row."""
    _, score_all = get_scorer(scorer)
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_all(records)
        all_scored.extend(scored)
        rows.append(
            aggregate(
                source,
                list(query.terms),
                scored,
                notes=notes,
                scorer=scorer,
            )
        )

    total_scored = all_scored
    total_dropped = 0
    if dedup:
        total_scored, total_dropped = dedupe_records(all_scored)
    rows.append(
        aggregate(
            "__total__",
            list(query.terms),
            total_scored,
            notes=notes,
            scorer=scorer,
            n_duplicates=total_dropped,
        )
    )
    return rows


BySourceFn = Callable[[SourceQuery], Mapping[str, list[VideoRecord]]]


def run_matrix(
    suite: SourceQuerySuite,
    by_source_fn: BySourceFn,
    notes: str = "",
    scorer: str = DEFAULT_SCORER,
    dedup: bool = False,
) -> dict[str, list[BenchmarkResult]]:
    """Run every query in `suite` and return
    `{"per_query": [rows...], "per_source": [rows...]}`.

    `per_query` rows carry the query's own terms; `per_source` rows
    aggregate a source across *all* queries in the suite so we can
    compare sources with reduced single-query variance.
    """
    per_query: list[BenchmarkResult] = []
    scored_by_source: dict[str, list[VideoRecord]] = {}
    total_dedup_dropped = 0

    for query in suite.queries:
        by_source = by_source_fn(query)
        rows = run_comparison(
            query,
            by_source,
            notes=notes,
            scorer=scorer,
            dedup=dedup,
        )
        per_query.extend(rows)
        _, score_all = get_scorer(scorer)
        for src, records in by_source.items():
            scored_by_source.setdefault(src, []).extend(score_all(records))
        total_row = next(r for r in rows if r.source == "__total__")
        total_dedup_dropped += total_row.n_duplicates

    per_source: list[BenchmarkResult] = []
    combined: list[VideoRecord] = []
    combined_terms = _suite_terms(suite)
    for src, recs in sorted(scored_by_source.items()):
        combined.extend(recs)
        per_source.append(
            aggregate(
                src,
                combined_terms,
                recs,
                notes=f"{notes};suite={suite.name}".strip(";"),
                scorer=scorer,
            )
        )
    if dedup:
        combined, dropped = dedupe_records(combined)
    else:
        dropped = 0
    per_source.append(
        aggregate(
            "__total__",
            combined_terms,
            combined,
            notes=f"{notes};suite={suite.name}".strip(";"),
            scorer=scorer,
            n_duplicates=dropped,
        )
    )
    return {"per_query": per_query, "per_source": per_source}


def _suite_terms(suite: SourceQuerySuite) -> list[str]:
    seen: list[str] = []
    for q in suite.queries:
        for t in q.terms:
            if t not in seen:
                seen.append(t)
    return seen
