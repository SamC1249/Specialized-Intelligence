"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through a scorer — emit a deterministic list of `BenchmarkResult` rows:
one per source plus an aggregate `__total__`.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.

Scorer choice is a first-class parameter: the same records can be
re-scored under scorer ``v1`` or ``v2`` (see
``specint.quality.SCORERS``) to produce head-to-head comparisons.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Iterable, Mapping

from specint.quality import get_scorer, score_records
from specint.records import BenchmarkResult, License, SourceQuery, VideoRecord

Scorer = Callable[[VideoRecord], float]


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


def _score_with(scorer: Scorer, records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(scorer(r)) for r in records]


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    scorer: Scorer | str | None = None,
) -> list[BenchmarkResult]:
    """Score, aggregate per source, and append a `__total__` row.

    ``scorer`` may be:
      - ``None`` (default): use the legacy ``score_records`` (v1) so the
        historical baseline is stable.
      - a string ``"v1"`` / ``"v2"``: dispatch via ``get_scorer``.
      - a callable ``VideoRecord -> float``.
    """
    if scorer is None:
        score_fn = None
    elif callable(scorer):
        score_fn = scorer
    else:
        score_fn = get_scorer(scorer)

    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    for source, records in sorted(by_source.items()):
        scored = score_records(records) if score_fn is None else _score_with(score_fn, records)
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))
    return rows


def head_to_head(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    scorers: Iterable[str] = ("v1", "v2"),
    notes: str = "",
) -> dict[str, list[BenchmarkResult]]:
    """Run the harness once per scorer, returning a scorer -> rows map.

    Used by the ``compare --head-to-head`` CLI path and the daily
    scorer-shootout report.
    """
    out: dict[str, list[BenchmarkResult]] = {}
    for name in scorers:
        rows = run_comparison(
            query,
            by_source,
            notes=f"{notes};scorer={name}" if notes else f"scorer={name}",
            scorer=name,
        )
        out[name] = rows
    return out
