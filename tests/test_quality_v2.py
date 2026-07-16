from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import get_scorer, score_records_by_name
from specint.quality import v2 as v2_mod
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_v2_registry_lookup():
    v2_scorer = get_scorer("v2")
    v1_scorer = get_scorer("v1")
    rich = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        title="Sourdough tutorial",
        description=(
            "In this five minute video we chop, saute, and simmer. "
            "We toast the bread, mix the dough, knead until elastic, "
            "and bake at 220 C for 30 minutes."
        ),
        recipe_steps=["chop", "saute", "deglaze", "toss"],
    )
    assert v2_scorer(rich) > 0.65
    assert v1_scorer(rich) > 0.65


def test_v2_penalises_empty_text_1080p_cc_by():
    """H2 fixture: a CC-BY 1080p record with an empty title/description
    should be clamped by the text-density minimum."""
    bare = _rec(license=License.CC_BY, height=1080, duration_s=300.0)
    v1 = get_scorer("v1")(bare)
    v2 = get_scorer("v2")(bare)
    assert v1 > 0.5, f"v1 should be inflated (proves the H2 problem), got {v1}"
    assert v2 <= v2_mod.TEXT_DENSITY_MIN_CAP + 1e-9, f"v2 should be capped, got {v2}"


def test_v2_procedural_verb_component_uses_lexicon():
    procedural = _rec(
        license=License.CC_BY,
        height=720,
        duration_s=300.0,
        title="Chop saute simmer bake",
        description="chop dice mince slice grate peel boil simmer saute fry",
    )
    barely = _rec(
        license=License.CC_BY,
        height=720,
        duration_s=300.0,
        title="Some cooking video here today",
        description="This has words but nothing procedural at all here today.",
    )
    v2 = get_scorer("v2")
    assert v2(procedural) > v2(barely)


def test_v2_english_signal_soft():
    en = _rec(
        license=License.CC_BY,
        height=720,
        duration_s=300.0,
        title="Sourdough tutorial with knife skills",
        description="English procedural narration " * 4,
        language="en",
    )
    other = _rec(
        license=License.CC_BY,
        height=720,
        duration_s=300.0,
        title="Sourdough tutorial with knife skills",
        description="English procedural narration " * 4,
        language=None,
    )
    v2 = get_scorer("v2")
    # English lang tag should push it up but not by much (≤ 0.05 weight).
    assert 0 <= v2(en) - v2(other) < 0.1


def test_score_records_by_name_dispatches():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [via_v1] = score_records_by_name([r], scorer="v1")
    [via_v2] = score_records_by_name([r], scorer="v2")
    assert via_v1.quality_score is not None
    assert via_v2.quality_score is not None
