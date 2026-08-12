"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs
— typically produced by feeding offline fixtures or live `search()`
calls through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

Optionally also run cross-source deduplication and return the overlap
matrix (see `specint.dedupe`). The CLI wraps this so
`python -m specint compare` always produces a reproducible,
JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedupe import dedupe, overlap
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
    """Score, aggregate per source, and append a `__total__` row."""

    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, query)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))
    return rows


def run_full_report(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    with_dedupe: bool = False,
) -> dict:
    """Return a full report dict: rows + optional dedupe/overlap section."""

    scored_by_source: dict[str, list[VideoRecord]] = {
        source: score_records(records, query) for source, records in sorted(by_source.items())
    }
    rows = run_comparison(query, scored_by_source, notes=notes)
    payload: dict = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    if with_dedupe:
        flat = [rec for recs in scored_by_source.values() for rec in recs]
        deduped = dedupe(flat)
        payload["dedupe"] = {
            "n_records": len(flat),
            "n_after_dedupe": len(deduped),
            "overlap": overlap(scored_by_source),
        }
    return payload
