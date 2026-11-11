"""Systematic comparison harness.

Given a `SourceQuery` and a mapping of `(source_slug -> list of raw
VideoRecords)` — typically produced by feeding offline fixtures or live
`search()` calls through a `QualityProfile` — emit a deterministic list
of `BenchmarkResult` rows, one per source plus an aggregate `__total__`.

Rows now carry:
  * `profile`              — which `QualityProfile` was used.
  * `n_unique_after_dedupe` — cluster count under `specint.dedupe` for
    this source (and, on the `__total__` row, the *cross-source* count,
    which is strictly the interesting number for yield reporting).

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping

from specint.dedupe import dedupe
from specint.quality.profiles import PROFILES, QualityProfile, get_profile
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
    profile: str = "baseline",
    n_unique_after_dedupe: int | None = None,
) -> BenchmarkResult:
    items = list(records)
    if not items:
        empty = BenchmarkResult.empty(source, query_terms, notes=notes, profile=profile)
        if n_unique_after_dedupe is not None:
            return empty.model_copy(update={"n_unique_after_dedupe": n_unique_after_dedupe})
        return empty

    qualities = [r.quality_score or 0.0 for r in items]
    durations = [r.duration_s or 0.0 for r in items]
    license_clean = sum(
        1 for r in items if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    authors = {r.author for r in items if r.author}
    unique = n_unique_after_dedupe if n_unique_after_dedupe is not None else len(dedupe(items))

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
        n_unique_after_dedupe=unique,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    profile: str | QualityProfile = "baseline",
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    `profile` may be a registered name (see `PROFILES`) or a
    `QualityProfile` instance, so callers can pass custom profiles
    without mutating the global registry.
    """
    qp = profile if isinstance(profile, QualityProfile) else get_profile(profile)

    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = qp.score_records(records)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes, profile=qp.name))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes, profile=qp.name))
    return rows


def available_profiles() -> list[str]:
    return sorted(PROFILES.keys())
