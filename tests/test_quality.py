from datetime import UTC, datetime

from specint.domains import COOKING, LABORATORY
from specint.quality import (
    component_values,
    score_record,
    score_record_v1,
    score_record_v2,
    score_records,
)
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
        recipe_steps=["chop garlic", "saute onions", "deglaze the pan"],
    )
    assert score_record(rich) > score_record(bare)
    assert score_record(rich) > 0.6


def test_score_records_attaches_quality():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [scored] = score_records([r])
    assert scored.quality_score is not None
    assert 0.0 <= scored.quality_score <= 1.0


def test_unknown_license_is_penalised_but_not_zero_in_v2():
    unknown = _rec(license=License.UNKNOWN, duration_s=300.0, height=1080)
    restricted = _rec(license=License.RESTRICTED, duration_s=300.0, height=1080)
    ccby = _rec(license=License.CC_BY, duration_s=300.0, height=1080)
    assert score_record_v2(unknown) > score_record_v2(restricted)
    assert score_record_v2(ccby) > score_record_v2(unknown)


def test_procedural_density_uses_domain_verbs():
    cooking_rec = _rec(
        title="chop garlic, saute onions, and simmer stock",
        description="",
    )
    lab_rec = _rec(
        title="pipette 10ul, centrifuge, resuspend and incubate",
        description="",
    )
    cv = component_values(cooking_rec, domain=COOKING)["procedural_density"]
    cv_lab = component_values(cooking_rec, domain=LABORATORY)["procedural_density"]
    assert cv > cv_lab

    lv_lab = component_values(lab_rec, domain=LABORATORY)["procedural_density"]
    lv_cook = component_values(lab_rec, domain=COOKING)["procedural_density"]
    assert lv_lab > lv_cook


def test_v1_scorer_is_still_available():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    v1 = score_record_v1(r)
    v2 = score_record_v2(r)
    assert 0.0 <= v1 <= 1.0
    assert 0.0 <= v2 <= 1.0


def test_all_v2_components_are_bounded_in_unit_interval():
    r = _rec(
        license=License.CC_BY_SA,
        duration_s=300.0,
        height=1080,
        description="x" * 5000,
        recipe_steps=["boil"] * 20,
    )
    for name, value in component_values(r).items():
        assert 0.0 <= value <= 1.0, f"{name}={value} out of range"
