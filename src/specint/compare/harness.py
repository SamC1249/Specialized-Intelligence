"""Systematic comparison harness.

Given a `SourceQuery` and a set of (source_slug, list_of_records) pairs —
typically produced by feeding offline fixtures or live `search()` calls
through `quality.score_records` — emit a deterministic list of
`BenchmarkResult` rows: one per source plus an aggregate `__total__`.

`run_comparison` returns the legacy `list[BenchmarkResult]` for
backward-compatibility with existing callers and tests.

`run_full_comparison` is the richer entrypoint added by
`docs/plan-2026-07-18.md`. It additionally returns:

  - Pareto frontier over `(mean_quality, license_clean_rate,
    unique_after_dedupe)` — a source is *dominated* if another source
    strictly beats it on all three axes; the frontier is the
    non-dominated set.
  - Cross-source `DedupeReport` when `dedupe=True`.
  - Per-source language coverage after optional heuristic detection.

The CLI wraps this so `python -m specint compare` always produces a
reproducible, JSON-serialisable artifact under `reports/`.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from specint.quality import annotate_language, dedupe, score_records
from specint.quality.dedupe import DedupeReport
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


def _apply_language_detection(records: list[VideoRecord]) -> list[VideoRecord]:
    return [
        r.model_copy(update={"language": annotate_language(r.title, r.description, r.language)})
        for r in records
    ]


@dataclass(frozen=True)
class ParetoPoint:
    source: str
    mean_quality: float
    license_clean_rate: float
    unique_after_dedupe: int

    def dominates(self, other: ParetoPoint) -> bool:
        return (
            self.mean_quality >= other.mean_quality
            and self.license_clean_rate >= other.license_clean_rate
            and self.unique_after_dedupe >= other.unique_after_dedupe
            and (
                self.mean_quality > other.mean_quality
                or self.license_clean_rate > other.license_clean_rate
                or self.unique_after_dedupe > other.unique_after_dedupe
            )
        )


def pareto_frontier(points: list[ParetoPoint]) -> list[str]:
    frontier: list[str] = []
    for p in points:
        if any(q.dominates(p) for q in points if q.source != p.source):
            continue
        frontier.append(p.source)
    return sorted(frontier)


@dataclass(frozen=True)
class ComparisonResult:
    rows: list[BenchmarkResult]
    dedupe_report: DedupeReport | None = None
    pareto: list[str] = field(default_factory=list)
    language_coverage: dict[str, float] = field(default_factory=dict)

    def to_payload(self, query: SourceQuery) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query.model_dump(mode="json"),
            "rows": [r.model_dump(mode="json") for r in self.rows],
        }
        if self.dedupe_report is not None:
            payload["dedupe"] = {
                "input_n": self.dedupe_report.input_n,
                "output_n": self.dedupe_report.output_n,
                "n_clusters_gt1": self.dedupe_report.n_clusters_gt1,
                "reduction": round(self.dedupe_report.reduction, 4),
                "clusters": [
                    {
                        "canonical_id": c.canonical_id,
                        "member_ids": list(c.member_ids),
                        "sources": list(c.sources),
                        "reason": c.reason,
                    }
                    for c in self.dedupe_report.clusters
                ],
            }
        if self.pareto:
            payload["pareto_frontier"] = self.pareto
        if self.language_coverage:
            payload["language_coverage"] = self.language_coverage
        return payload


def run_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
) -> list[BenchmarkResult]:
    """Legacy entrypoint kept for back-compat. See `run_full_comparison`."""
    return run_full_comparison(query, by_source, notes=notes).rows


def run_full_comparison(
    query: SourceQuery,
    by_source: Mapping[str, list[VideoRecord]],
    notes: str = "",
    *,
    detect_language: bool = False,
    apply_dedupe: bool = False,
) -> ComparisonResult:
    rows: list[BenchmarkResult] = []
    all_scored: list[VideoRecord] = []
    per_source_scored: dict[str, list[VideoRecord]] = {}
    language_coverage: dict[str, float] = {}

    for source, records in sorted(by_source.items()):
        prepared = list(records)
        if detect_language:
            prepared = _apply_language_detection(prepared)
        scored = score_records(prepared)
        per_source_scored[source] = scored
        all_scored.extend(scored)
        rows.append(aggregate(source, query.terms, scored, notes=notes))
        if scored:
            language_coverage[source] = round(sum(1 for r in scored if r.language) / len(scored), 4)
        else:
            language_coverage[source] = 0.0

    dedupe_report: DedupeReport | None = None
    unique_after_dedupe_by_source: dict[str, int] = {
        src: len(recs) for src, recs in per_source_scored.items()
    }

    if apply_dedupe:
        canonical, dedupe_report = dedupe(all_scored)
        rows.append(aggregate("__total_deduped__", query.terms, canonical, notes=notes))
        survivor_ids = {r.id for r in canonical}
        for src, recs in per_source_scored.items():
            unique_after_dedupe_by_source[src] = sum(1 for r in recs if r.id in survivor_ids)

    rows.append(aggregate("__total__", query.terms, all_scored, notes=notes))

    points: list[ParetoPoint] = []
    for src, recs in per_source_scored.items():
        if not recs:
            continue
        clean = sum(
            1 for r in recs if r.license is not License.UNKNOWN and r.license.is_redistributable
        )
        points.append(
            ParetoPoint(
                source=src,
                mean_quality=float(statistics.fmean(r.quality_score or 0.0 for r in recs)),
                license_clean_rate=clean / len(recs),
                unique_after_dedupe=unique_after_dedupe_by_source.get(src, len(recs)),
            )
        )
    pareto = pareto_frontier(points) if points else []

    return ComparisonResult(
        rows=rows,
        dedupe_report=dedupe_report,
        pareto=pareto,
        language_coverage=language_coverage,
    )
