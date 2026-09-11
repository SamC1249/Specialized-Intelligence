"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

Added 2026-09-11:
  - `profile`: select v1 (legacy) or v2 (procedural-density) quality
    weights. Recorded on every row.
  - `dedup`: apply the cross-source deduplicator before aggregating.
    Per-source rows still count their raw contribution (`n_records`),
    but every row also carries `n_unique` and `duplicate_rate` so the
    downstream diff is trivial.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedup import DedupReport, dedupe
from specint.quality import Profile, score_records
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
    profile: str = "v1",
    n_unique: int | None = None,
    duplicate_rate: float = 0.0,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        empty = BenchmarkResult.empty(source, query_terms, notes=notes, profile=profile)
        return empty.model_copy(
            update={"n_unique": n_unique or 0, "duplicate_rate": duplicate_rate}
        )

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
        profile=profile,
        n_unique=n_unique if n_unique is not None else len(items),
        duplicate_rate=duplicate_rate,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    profile: Profile = "v1",
    dedup: bool = False,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    When `dedup=True`, cross-source duplicates are detected across the
    union of all records. Each per-source row's `n_unique` counts how
    many of its records survived the dedup; the aggregate `__total__`
    row's `n_records` is the raw union count and its `n_unique` is the
    deduped count.
    """
    rows: list[BenchmarkResult] = []
    per_source_scored: dict[str, list[VideoRecord]] = {}
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, profile=profile)
        per_source_scored[source] = scored
        all_scored.extend(scored)

    kept_ids: set[str] | None = None
    dedup_report: DedupReport | None = None
    if dedup:
        kept, dedup_report = dedupe(all_scored)
        kept_ids = {r.id for r in kept}

    for source, scored in per_source_scored.items():
        if kept_ids is not None:
            unique_here = sum(1 for r in scored if r.id in kept_ids)
            dup_rate = 1.0 - (unique_here / len(scored)) if scored else 0.0
        else:
            unique_here = len(scored)
            dup_rate = 0.0
        rows.append(
            aggregate(
                source,
                query.terms,
                scored,
                notes=notes,
                profile=profile,
                n_unique=unique_here,
                duplicate_rate=dup_rate,
            )
        )

    total_unique = len(kept_ids) if kept_ids is not None else len(all_scored)
    total_dup_rate = dedup_report.duplicate_rate if dedup_report else 0.0
    rows.append(
        aggregate(
            "__total__",
            query.terms,
            all_scored,
            notes=notes,
            profile=profile,
            n_unique=total_unique,
            duplicate_rate=total_dup_rate,
        )
    )
    return rows
