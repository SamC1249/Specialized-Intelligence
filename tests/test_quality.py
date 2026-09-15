from datetime import UTC, datetime

import pytest

from specint.quality import SCORING_PROFILES, score_record, score_records
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


def test_procedural_verbs_boost_score():
    bland = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        title="A relaxing afternoon by the lake",
        description="A calm scenic tour with slow pacing and no instructions at all.",
    )
    procedural = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        title="Chop, sear, deglaze, and simmer",
        description="Chop garlic. Sear the steak. Deglaze the pan. Simmer until reduced.",
        recipe_steps=["chop garlic", "sear steak", "deglaze pan", "simmer sauce"],
    )
    assert score_record(procedural) > score_record(bland)


def test_named_profiles_are_all_normalised():
    r = _rec(license=License.CC_BY, duration_s=300.0, height=1080)
    for name in SCORING_PROFILES:
        s = score_record(r, profile=name)
        assert 0.0 <= s <= 1.0


def test_unknown_profile_raises():
    r = _rec()
    with pytest.raises(KeyError):
        score_record(r, profile="nonexistent")


def test_license_first_profile_penalises_unknown_license_more():
    unknown = _rec(license=License.UNKNOWN, duration_s=300.0, height=1080)
    balanced = score_record(unknown, profile="balanced")
    license_first = score_record(unknown, profile="license_first")
    assert license_first < balanced
