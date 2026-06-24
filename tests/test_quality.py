from datetime import UTC, datetime

from specint.quality import WEIGHTS, component_scores, score_record, score_records
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


def test_license_confidence_modulates_license_clean():
    high = _rec(license=License.CC_BY, license_confidence=1.0)
    low = _rec(license=License.CC_BY, license_confidence=0.3)
    assert component_scores(high)["license_clean"] == 1.0
    assert component_scores(low)["license_clean"] == 0.3
    assert score_record(high) > score_record(low)


def test_unknown_license_zero_regardless_of_confidence():
    r = _rec(license=License.UNKNOWN, license_confidence=1.0)
    assert component_scores(r)["license_clean"] == 0.0


def test_procedural_density_rewards_recipe_steps_and_verbs():
    plain = _rec(title="Plated dinner")
    proc = _rec(
        title="Step 1: chop onions",
        description="Stir, simmer, then serve.",
        recipe_steps=["Chop", "Sauté", "Stir", "Simmer", "Serve", "Plate"],
    )
    proc_score = component_scores(proc)["procedural_density"]
    plain_score = component_scores(plain)["procedural_density"]
    assert proc_score > plain_score
    assert proc_score >= 0.9


def test_weights_override_can_zero_a_component():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080, recipe_steps=["a"])
    w = dict(WEIGHTS)
    w["license_clean"] = 0.0
    no_license = score_record(r, weights=w)
    with_license = score_record(r)
    assert with_license > no_license
