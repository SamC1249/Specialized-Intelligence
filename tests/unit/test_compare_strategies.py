from __future__ import annotations

from specint.compare.strategies import (
    StrategyResult,
    compare_strategies,
    jaccard,
    strategy_overlap_matrix,
)
from specint.records import License, Provenance, VideoRecord


def _rec(idx: int, **kw) -> VideoRecord:
    base = {
        "id": f"r:{idx}",
        "source": "wikimedia",
        "source_native_id": str(idx),
        "url": f"https://example.org/{idx}",
        "title": f"recipe {idx}",
        "description": "Italian pasta and tomato sauce; how to cook at home.",
        "license": License.CC_BY,
        "provenance": Provenance(extractor="t"),
        "duration_s": 60.0 + 30.0 * idx,
        "height": 720 if idx % 2 == 0 else 360,
        "recipe_steps": ["a", "b"] if idx % 3 == 0 else [],
    }
    base.update(kw)
    return VideoRecord(**base)


def test_empty_pool_returns_empty():
    assert compare_strategies([], k=5) == []


def test_returns_one_result_per_strategy_in_sorted_order():
    pool = [_rec(i) for i in range(8)]
    results = compare_strategies(pool, k=3)
    names = [r.strategy for r in results]
    assert names == sorted(names)
    assert set(names) >= {
        "license_confidence",
        "license_then_wm",
        "quality_metadata",
        "random_baseline",
        "wm_utility",
    }


def test_each_result_has_k_or_fewer_selected():
    pool = [_rec(i) for i in range(8)]
    results = compare_strategies(pool, k=4)
    for r in results:
        assert len(r.selected_ids) <= 4


def test_random_baseline_deterministic_under_seed():
    pool = [_rec(i) for i in range(10)]
    a = compare_strategies(pool, k=5, seed=42)
    b = compare_strategies(pool, k=5, seed=42)
    by_name_a = {r.strategy: r.selected_ids for r in a}
    by_name_b = {r.strategy: r.selected_ids for r in b}
    assert by_name_a["random_baseline"] == by_name_b["random_baseline"]


def test_overlap_matrix_is_symmetric_with_unit_diagonal():
    pool = [_rec(i) for i in range(6)]
    results = compare_strategies(pool, k=3)
    matrix = strategy_overlap_matrix(results)
    for name in matrix:
        assert matrix[name][name] == 1.0
        for other in matrix:
            assert matrix[name][other] == matrix[other][name]


def test_jaccard_basic():
    assert jaccard([], []) == 1.0
    assert jaccard(["a"], ["a"]) == 1.0
    assert jaccard(["a"], ["b"]) == 0.0
    assert jaccard(["a", "b"], ["b", "c"]) == 1 / 3


def test_strategy_result_serializable():
    pool = [_rec(i) for i in range(5)]
    results = compare_strategies(pool, k=2)
    d = results[0].to_dict()
    assert isinstance(d, dict)
    for key in (
        "strategy",
        "k",
        "selected_ids",
        "mean_quality",
        "mean_wm_utility",
        "mean_license_confidence",
        "license_clean_ratio",
        "unique_authors",
        "total_duration_s",
    ):
        assert key in d
    assert isinstance(results[0], StrategyResult)
