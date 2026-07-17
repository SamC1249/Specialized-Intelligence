"""Unit tests for the ablation harness."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.compare.ablation import default_configs, run_ablation
from specint.quality.metrics import WeightConfig
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(**over) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="cooking pasta",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(over)
    return VideoRecord(**base)


def test_default_configs_include_default_and_alternatives():
    names = {cfg.name for cfg in default_configs()}
    assert "default" in names
    assert "license-only" in names


def test_run_ablation_produces_ranking_per_config():
    query = SourceQuery(terms=["cooking"])
    by_source = {
        "a": [_rec(id="a:1", source="a", license=License.CC0, height=1080, duration_s=300.0)],
        "b": [_rec(id="b:1", source="b", license=License.UNKNOWN, height=240, duration_s=10.0)],
    }
    result = run_ablation(query, by_source)
    assert "default" in result["configs"]
    default_ranking = result["rankings"]["default"]
    assert default_ranking[0]["source"] == "a"
    assert set(result["delta_vs_default"].keys()) <= set(result["configs"]) - {"default"}


def test_run_ablation_rejects_empty_configs():
    query = SourceQuery(terms=["cooking"])
    try:
        run_ablation(query, {"a": [_rec()]}, configs=[])
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty configs")


def test_weight_config_score_matches_underlying_scorer():
    r = _rec(license=License.CC0, height=1080, duration_s=300.0)
    cfg = WeightConfig(name="license-only", weights={"license_clean": 1.0})
    assert cfg.score(r) == 1.0
