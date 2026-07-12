"""Systematic comparison harness.

Given a `SourceQuery`, a domain, and a set of `(source_slug, records)`
pairs — typically produced by feeding offline fixtures or live
`search()` calls through `quality.score_records` — emit a deterministic
list of `BenchmarkResult` rows: one per source, one `__total__` (pre
dedup), and one `__total_deduped__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

Dedup runs on the combined `all-scored` list (not per-source) because
cross-source dedup is where the real inflation happens.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.domains import DEFAULT_DOMAIN, Domain
from specint.pipeline import dedup_records
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
    domain: Domain = DEFAULT_DOMAIN,
    with_dedup: bool = True,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append pre-/post-dedup totals.

    Determinism: sources are iterated in sorted-slug order; the dedup
    survivor selection is also deterministic (see `dedup_records`).
    """
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records, domain=domain)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))
    if with_dedup:
        deduped = dedup_records(all_scored)
        rows.append(
            aggregate(
                "__total_deduped__",
                query.terms,
                deduped.records,
                notes=f"{notes};n_dropped={len(all_scored) - len(deduped.records)}",
            )
        )
    return rows


__all__ = ["aggregate", "run_comparison"]
