"""Systematic comparison harness.

Given a `SourceQuery` (or `SourceQuerySuite`) and a set of
(source_slug, list_of_records) pairs — typically produced by feeding
offline fixtures or live `search()` calls — emit a deterministic
list of `BenchmarkResult` rows: one per source plus an aggregate
`__total__`.

Two entry points:

- `run_comparison(query, by_source, scorer=..., dedup=..., notes=...)`
  runs a single query.
- `run_matrix(suite, by_query_source, scorer=..., dedup=..., notes=...)`
  runs each query in a `SourceQuerySuite` and returns per-(query,
  source) rows plus a per-source aggregate. Callers who need a
  single-number report can `aggregate_matrix` afterwards.

Determinism: sources are iterated in `sorted` order and duplicate
records (by `VideoRecord.id`) are collapsed within each source before
scoring. Duplicate collapses are counted on the corresponding
`BenchmarkResult.n_duplicates`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.quality import get_batch_scorer
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


def _dedup_by_id(records: Iterable[VideoRecord]) -> tuple[list[VideoRecord], int]:
    seen: set[str] = set()
    unique: list[VideoRecord] = []
    duplicates = 0
    for record in records:
        if record.id in seen:
            duplicates += 1
            continue
        seen.add(record.id)
        unique.append(record)
    return unique, duplicates


def aggregate(
    source: str,
    query_terms: list[str],
    records: Iterable[VideoRecord],
    notes: str = "",
    scorer: str = "v1",
    n_duplicates: int = 0,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        return BenchmarkResult.empty(source, query_terms, notes=notes, scorer=scorer)

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
        n_duplicates=n_duplicates,
        scorer=scorer,
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    scorer: str = "v1",
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    Records with duplicate `id`s within a source are collapsed before
    scoring; the count is reported via `BenchmarkResult.n_duplicates`.
    """
    batch_scorer = get_batch_scorer(scorer)
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    total_duplicates = 0
    for source, records in sorted(by_source.items()):
        unique, dups = _dedup_by_id(records)
        scored = batch_scorer(unique)
        all_scored.extend(scored)
        total_duplicates += dups
        rows.append(
            aggregate(
                source,
                query.terms,
                scored,
                notes=notes,
                scorer=scorer,
                n_duplicates=dups,
            )
        )
    rows.append(
        aggregate(
            "__total__",
            query.terms,
            all_scored,
            notes=notes,
            scorer=scorer,
            n_duplicates=total_duplicates,
        )
    )
    return rows


def run_matrix(
    suite: SourceQuerySuite,
    by_query_source: Mapping[str, Mapping[str, list[VideoRecord]]],
    notes: str = "",
    scorer: str = "v1",
) -> list[BenchmarkResult]:
    """Multi-query matrix.

    `by_query_source` is a mapping keyed by `SourceQuery.serialize()`
    → source slug → records. This keeps the harness pure: callers are
    responsible for wiring fixtures or live `search()` calls to the
    right query. The harness returns per-(query, source) rows plus a
    per-source aggregate across all queries and a grand `__total__`.
    """
    rows: list[BenchmarkResult] = []
    per_source_records: dict[str, list[VideoRecord]] = {}
    per_source_dups: dict[str, int] = {}

    for query in suite.queries:
        key = query.serialize()
        by_source = dict(by_query_source.get(key, {}))
        sub_rows = run_comparison(
            query,
            by_source,
            notes=f"{notes}|{suite.name}|{key}",
            scorer=scorer,
        )
        rows.extend(r for r in sub_rows if r.source != "__total__")
        for row in sub_rows:
            if row.source == "__total__":
                continue
            per_source_records.setdefault(row.source, [])
            per_source_dups[row.source] = per_source_dups.get(row.source, 0) + row.n_duplicates
        # Roll the already-scored records into the per-source pool
        # for the aggregate row using the same scorer.
        for source, records in by_source.items():
            unique, _ = _dedup_by_id(records)
            per_source_records[source].extend(get_batch_scorer(scorer)(unique))

    all_terms: list[str] = []
    for q in suite.queries:
        all_terms.extend(q.terms)

    for source, records in sorted(per_source_records.items()):
        rows.append(
            aggregate(
                source,
                all_terms,
                records,
                notes=f"{notes}|{suite.name}|__suite_aggregate__",
                scorer=scorer,
                n_duplicates=per_source_dups.get(source, 0),
            )
        )

    total_records: list[VideoRecord] = []
    for records in per_source_records.values():
        total_records.extend(records)
    rows.append(
        aggregate(
            "__total__",
            all_terms,
            total_records,
            notes=f"{notes}|{suite.name}|__suite_aggregate__",
            scorer=scorer,
            n_duplicates=sum(per_source_dups.values()),
        )
    )
    return rows
