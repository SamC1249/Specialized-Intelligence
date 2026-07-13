from datetime import UTC, datetime

from specint.quality import component_scores, score_record, score_records
from specint.quality.metrics import WEIGHTS
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Some cooking video",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_score_minimum_record_is_low():
    r = _rec()
    assert 0.0 <= score_record(r) < 0.2


def test_score_uses_license_and_resolution():
    bare = _rec()
    rich = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        description="A 5-minute knife skills tutorial." * 10,
        recipe_steps=["chop", "saute", "deglaze"],
    )
    assert score_record(rich) > score_record(bare)
    assert score_record(rich) > 0.7


def test_score_records_attaches_quality():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [scored] = score_records([r])
    assert scored.quality_score is not None
    assert 0.0 <= scored.quality_score <= 1.0


def test_component_scores_expose_all_components():
    r = _rec(license=License.CC_BY, duration_s=300.0, height=1080, recipe_steps=["a", "b"])
    comps = component_scores(r)
    assert set(comps) == set(WEIGHTS)
    for v in comps.values():
        assert 0.0 <= v <= 1.0


def test_procedural_density_rewards_more_steps():
    few = _rec(license=License.CC_BY, recipe_steps=["a"])
    many = _rec(
        license=License.CC_BY,
        recipe_steps=[f"step {i}" for i in range(8)],
    )
    assert (
        component_scores(many)["procedural_density"] > component_scores(few)["procedural_density"]
    )


def test_language_component_uses_detector():
    silent = _rec(license=License.CC_BY, title="x")
    verbose = _rec(
        license=License.CC_BY,
        title="How to make a classic French onion soup, step by step",
        description=(
            "A slow simmered French onion soup with caramelised onions thyme "
            "gruyere toast and a splash of dry white wine every step timed and captioned."
        ),
    )
    assert (
        component_scores(verbose)["language_confidence"]
        > component_scores(silent)["language_confidence"]
    )


def test_custom_weights_do_not_mutate_default():
    r = _rec(license=License.CC_BY, duration_s=300.0, height=1080)
    baseline = score_record(r)
    override = {k: (1.0 if k == "resolution" else 0.0) for k in WEIGHTS}
    scored = score_record(r, weights=override)
    assert scored == 1.0
    assert WEIGHTS["license_clean"] > 0.0
    assert score_record(r) == baseline
