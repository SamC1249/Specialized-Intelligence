from __future__ import annotations

from specint.compare.ranking import compare_runs
from specint.records import BenchmarkResult


def _row(
    mean_q: float, unique: int, clean: int, clean_ratio: float, proc: float, langs: list[str]
) -> BenchmarkResult:
    return BenchmarkResult(
        source="__total__",
        query_terms=["cooking"],
        n_records=unique,
        n_license_clean=clean,
        total_duration_s=100.0,
        mean_quality=mean_q,
        p50_quality=mean_q,
        p90_quality=mean_q,
        unique_authors=1,
        n_unique_after_dedup=unique,
        license_clean_ratio=clean_ratio,
        mean_procedural_density=proc,
        languages_seen=langs,
    )


def test_verdict_tie_for_identical_runs():
    a = [_row(0.5, 3, 2, 0.66, 0.4, ["en"])]
    b = [_row(0.5, 3, 2, 0.66, 0.4, ["en"])]
    delta = compare_runs(a, b)
    assert delta.verdict == "tie"


def test_verdict_dominates_when_strictly_better():
    a = [_row(0.5, 3, 2, 0.66, 0.4, ["en"])]
    b = [_row(0.6, 4, 3, 0.75, 0.5, ["en", "es"])]
    delta = compare_runs(a, b)
    assert delta.verdict == "dominates"


def test_verdict_mixed_when_one_better_one_worse():
    a = [_row(0.5, 3, 2, 0.66, 0.4, ["en"])]
    b = [_row(0.6, 2, 3, 0.75, 0.5, ["en"])]
    delta = compare_runs(a, b)
    assert delta.verdict == "mixed"


def test_verdict_dominated_when_worse():
    a = [_row(0.6, 4, 3, 0.75, 0.5, ["en", "es"])]
    b = [_row(0.5, 3, 2, 0.66, 0.4, ["en"])]
    delta = compare_runs(a, b)
    assert delta.verdict == "dominated"
