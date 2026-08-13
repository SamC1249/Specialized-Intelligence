"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from typing import Any

from specint.dedupe import dedupe, dedupe_by_source, overlap
from specint.quality import detect_language, score_records
from specint.records import BenchmarkResult, License, SourceQuery, VideoRecord


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    k = max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1))))
    return s[k]


def _mean_language_confidence(records: Iterable[VideoRecord]) -> float:
    confs: list[float] = []
    for r in records:
        text = r.title
        if r.description:
            text = f"{text} {r.description}"
        _, conf = detect_language(text)
        confs.append(conf)
    return float(statistics.fmean(confs)) if confs else 0.0


def aggregate(
    source: str,
    query_terms: list[str],
    records: Iterable[VideoRecord],
    notes: str = "",
    n_before_dedupe: int | None = None,
) -> BenchmarkResult:
    items = list(records)
    if not items and n_before_dedupe is None:
        return BenchmarkResult.empty(source, query_terms, notes=notes)

    qualities = [r.quality_score or 0.0 for r in items]
    durations = [r.duration_s or 0.0 for r in items]
    license_clean = sum(
        1 for r in items if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    authors = {r.author for r in items if r.author}
    n_before = n_before_dedupe if n_before_dedupe is not None else len(items)
    duplicates = max(0, n_before - len(items))

    return BenchmarkResult(
        source=source,
        query_terms=list(query_terms),
        n_records=n_before,
        n_license_clean=license_clean,
        total_duration_s=float(sum(durations)),
        mean_quality=float(statistics.fmean(qualities)) if qualities else 0.0,
        p50_quality=_percentile(qualities, 50),
        p90_quality=_percentile(qualities, 90),
        unique_authors=len(authors),
        n_after_dedupe=len(items),
        n_duplicates=duplicates,
        mean_language_confidence=_mean_language_confidence(items),
        notes=notes,
    )


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    dedupe_enabled: bool = False,
    include_overlap: bool = False,
) -> list[BenchmarkResult]:
    """Score, optionally dedupe, aggregate per source, and append __total__.

    When `dedupe_enabled` is True we run `dedupe_by_source` before
    aggregation so per-source rows reflect *post-dedupe* winners and
    `n_records` still reports the raw pre-dedupe count.
    """
    rows: list[BenchmarkResult] = []
    all_before: list[VideoRecord] = []

    scored_by_source: dict[str, list[VideoRecord]] = {}
    for source, records in sorted(by_source.items()):
        scored = score_records(records, target_language=query.language)
        scored_by_source[source] = scored
        all_before.extend(scored)

    if dedupe_enabled:
        winners, _ = dedupe_by_source(scored_by_source)
        for source in sorted(scored_by_source.keys()):
            rows.append(
                aggregate(
                    source,
                    query.terms,
                    winners.get(source, []),
                    notes=notes,
                    n_before_dedupe=len(scored_by_source[source]),
                )
            )
        total_after, _ = dedupe(all_before)
        rows.append(
            aggregate(
                "__total__",
                query.terms,
                total_after,
                notes=notes,
                n_before_dedupe=len(all_before),
            )
        )
    else:
        for source in sorted(scored_by_source.keys()):
            rows.append(aggregate(source, query.terms, scored_by_source[source], notes=notes))
        rows.append(aggregate("__total__", query.terms, all_before, notes=notes))

    return rows


def build_report(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    dedupe_enabled: bool = False,
) -> dict[str, Any]:
    """One-stop wrapper: run the harness and produce a JSON-ready payload."""
    rows = run_comparison(
        query,
        by_source,
        notes=notes,
        dedupe_enabled=dedupe_enabled,
    )
    payload: dict[str, Any] = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
        "dedupe_enabled": dedupe_enabled,
    }
    payload["overlap"] = overlap(by_source)
    return payload
