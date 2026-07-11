from datetime import UTC, datetime

from specint.quality import get_scorer
from specint.quality.metrics_v2 import (
    LICENSE_TIER,
    PROCEDURAL_VERBS,
    component_breakdown,
    score_record,
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


def test_v2_license_tier_ordering():
    assert LICENSE_TIER[License.CC0] > LICENSE_TIER[License.PUBLIC_DOMAIN]
    assert LICENSE_TIER[License.PUBLIC_DOMAIN] > LICENSE_TIER[License.CC_BY]
    assert LICENSE_TIER[License.CC_BY] > LICENSE_TIER[License.CC_BY_SA]
    assert LICENSE_TIER[License.CC_BY_SA] > LICENSE_TIER[License.OTHER_FREE]
    assert LICENSE_TIER[License.UNKNOWN] == 0.0
    assert LICENSE_TIER[License.RESTRICTED] == 0.0


def test_v2_procedural_verbs_include_common_actions():
    for verb in ("chop", "saute", "sauté", "simmer", "reduce", "whisk"):
        assert verb in PROCEDURAL_VERBS


def test_v2_neutral_when_metadata_missing_is_between_v1_and_perfect():
    # A record with unknown height/duration should not be zero-scored on
    # those axes; that's the whole point of v2.
    r = _rec(license=License.CC_BY)
    breakdown = component_breakdown(r)
    assert breakdown["resolution"] == 0.5
    assert breakdown["duration"] == 0.5


def test_v2_procedural_density_rewards_recipe_language():
    plain = _rec(license=License.CC_BY, description="a video")
    proc = _rec(
        license=License.CC_BY,
        description="Chop garlic, sauté in butter, simmer with cream, whisk in cheese.",
    )
    assert (
        component_breakdown(proc)["procedural_density"]
        > component_breakdown(plain)["procedural_density"]
    )


def test_v2_rich_record_scores_higher_than_bare():
    bare = _rec()
    rich = _rec(
        license=License.CC0,
        duration_s=300.0,
        height=1080,
        fps=30.0,
        language="en",
        description="A 5-minute knife skills tutorial." * 5,
        recipe_steps=[
            "Chop the onions finely.",
            "Sauté in butter until golden.",
            "Deglaze with white wine and simmer.",
        ],
    )
    assert score_record(rich) > score_record(bare)
    assert score_record(rich) > 0.7


def test_v2_score_records_attaches_quality_in_bounds():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [scored] = score_records([r])
    assert scored.quality_score is not None
    assert 0.0 <= scored.quality_score <= 1.0


def test_get_scorer_dispatch():
    v1 = get_scorer("v1")
    v2 = get_scorer("v2")
    r = _rec(license=License.CC_BY, duration_s=300.0, height=1080)
    assert 0.0 <= v1(r) <= 1.0
    assert 0.0 <= v2(r) <= 1.0
    assert v1 is not v2


def test_get_scorer_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        get_scorer("v99")


def test_v2_high_fps_bonus_below_ceiling():
    slow = _rec(license=License.CC_BY, height=720, fps=24.0)
    fast = _rec(license=License.CC_BY, height=720, fps=60.0)
    assert component_breakdown(fast)["resolution"] > component_breakdown(slow)["resolution"]


def test_v2_low_fps_penalty():
    normal = _rec(license=License.CC_BY, height=720, fps=24.0)
    stop_motion = _rec(license=License.CC_BY, height=720, fps=8.0)
    assert (
        component_breakdown(normal)["resolution"] > component_breakdown(stop_motion)["resolution"]
    )
