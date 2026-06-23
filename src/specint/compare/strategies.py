"""Strategy comparison: rank-and-prune the same record pool with multiple
scoring strategies and measure how their top-K subsets differ.

This is the *systematic* comparison the daily plan repeatedly asks for:
not "which adapter ran today" but "given an identical candidate pool,
does the WM-utility ranker pick a measurably different subset than the
metadata-only quality scorer or a random baseline?"

A `StrategyResult` is the deterministic, JSON-serialisable answer.

Inputs:
  * records: list[VideoRecord] (already deduped at the candidate level)
  * k: int — top-K to retain per strategy
  * seed: int — for the random baseline

Outputs:
  * `compare_strategies(records, k=...) -> list[StrategyResult]`
  * Each StrategyResult is comparable cross-run.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

from specint.license_confidence import score_license_confidence
from specint.quality.metrics import score_record
from specint.records import License, VideoRecord
from specint.wm_utility import wm_utility_score


@dataclass
class StrategyResult:
    strategy: str
    k: int
    selected_ids: list[str] = field(default_factory=list)
    mean_quality: float = 0.0
    mean_wm_utility: float = 0.0
    mean_license_confidence: float = 0.0
    license_clean_ratio: float = 0.0
    unique_authors: int = 0
    total_duration_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _select(records: list[VideoRecord], scorer, k: int) -> list[VideoRecord]:
    keyed = [(scorer(r), r) for r in records]
    keyed.sort(key=lambda kv: (-kv[0], kv[1].id))
    return [r for _, r in keyed[:k]]


def _summarise(name: str, k: int, subset: list[VideoRecord]) -> StrategyResult:
    if not subset:
        return StrategyResult(strategy=name, k=k)
    qualities = [score_record(r) for r in subset]
    wm_scores = [wm_utility_score(r) for r in subset]
    lic_confs = [score_license_confidence(r) for r in subset]
    license_clean = sum(
        1 for r in subset if r.license is not License.UNKNOWN and r.license.is_redistributable
    )
    durations = [r.duration_s or 0.0 for r in subset]
    authors = {r.author for r in subset if r.author}
    return StrategyResult(
        strategy=name,
        k=k,
        selected_ids=sorted(r.id for r in subset),
        mean_quality=statistics.fmean(qualities),
        mean_wm_utility=statistics.fmean(wm_scores),
        mean_license_confidence=statistics.fmean(lic_confs),
        license_clean_ratio=license_clean / len(subset),
        unique_authors=len(authors),
        total_duration_s=float(sum(durations)),
    )


def compare_strategies(
    records: list[VideoRecord],
    k: int = 10,
    seed: int = 1729,
) -> list[StrategyResult]:
    pool = list(records)
    if not pool:
        return []

    strategies: dict[str, list[VideoRecord]] = {}

    strategies["quality_metadata"] = _select(pool, score_record, k)
    strategies["wm_utility"] = _select(pool, wm_utility_score, k)
    strategies["license_confidence"] = _select(pool, score_license_confidence, k)
    strategies["license_then_wm"] = _select(
        [r for r in pool if r.license.is_redistributable], wm_utility_score, k
    )
    rng = random.Random(seed)
    shuffled = pool[:]
    rng.shuffle(shuffled)
    strategies["random_baseline"] = shuffled[:k]

    return [_summarise(name, k, subset) for name, subset in sorted(strategies.items())]


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def strategy_overlap_matrix(results: list[StrategyResult]) -> dict[str, dict[str, float]]:
    """Pairwise Jaccard overlap of selected_ids per strategy."""
    matrix: dict[str, dict[str, float]] = {}
    for a in results:
        row: dict[str, float] = {}
        for b in results:
            row[b.strategy] = jaccard(a.selected_ids, b.selected_ids)
        matrix[a.strategy] = dict(sorted(row.items()))
    return dict(sorted(matrix.items()))
