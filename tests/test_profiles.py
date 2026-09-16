"""Scoring profiles + `score_record(profile=...)` tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.quality import get_profile, score_record
from specint.quality.profiles import BASELINE, COOKING, PROFILES
from specint.records import License, Provenance, VideoRecord


def _prov() -> Provenance:
    return Provenance(extractor="t", fetched_at=datetime.now(UTC), query="")


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking recipe demo",
        description="Kitchen basics.",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        recipe_steps=["chop", "boil", "serve"],
        provenance=_prov(),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_profiles_registry_covers_named_ones():
    assert "baseline" in PROFILES
    assert "cooking" in PROFILES
    assert get_profile("baseline") == BASELINE
    assert get_profile("cooking") == COOKING


def test_get_profile_unknown_raises():
    with pytest.raises(KeyError):
        get_profile("nope")


def test_baseline_profile_used_by_default():
    r = _rec()
    default = score_record(r)
    baseline = score_record(r, profile="baseline")
    assert default == pytest.approx(baseline)


def test_cooking_profile_rewards_relevant_records_more():
    relevant = _rec(title="Cooking pasta carbonara", description="A recipe demo.")
    generic = _rec(title="Studio recording", description="Video capture.")
    baseline_gap = score_record(relevant, profile="baseline") - score_record(
        generic, profile="baseline"
    )
    cooking_gap = score_record(relevant, profile="cooking") - score_record(
        generic, profile="cooking"
    )
    assert cooking_gap > baseline_gap


def test_profiles_can_be_dict_literals():
    r = _rec()
    score = score_record(r, profile={"license_clean": 1.0})
    assert score == pytest.approx(1.0)


def test_unknown_component_raises():
    r = _rec()
    with pytest.raises(KeyError):
        score_record(r, profile={"nope": 1.0})
