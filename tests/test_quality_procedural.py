"""Procedural quality signals + WEIGHTS_EXPERIMENTAL A/B semantics."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import WEIGHTS, WEIGHTS_EXPERIMENTAL, score_record, score_records
from specint.quality.procedural import (
    load_cooking_verbs,
    score_aspect_ratio,
    score_audio_present,
    score_cooking_verbs,
    score_shot_density_from_metadata,
)
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking demo",
        provenance=Provenance(
            extractor="t",
            fetched_at=datetime.now(UTC),
            query="q",
            raw_sha256="0" * 64,
        ),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_aspect_ratio_prefers_16_9_and_penalises_vertical():
    landscape = _rec(width=1920, height=1080)
    vertical = _rec(width=1080, height=1920)
    assert score_aspect_ratio(landscape) == 1.0
    assert score_aspect_ratio(vertical) is not None
    assert score_aspect_ratio(vertical) < 0.25
    assert score_aspect_ratio(_rec()) is None


def test_audio_present_returns_none_when_unknown():
    assert score_audio_present(_rec(audio_present=True)) == 1.0
    assert score_audio_present(_rec(audio_present=False)) == 0.0
    assert score_audio_present(_rec()) is None


def test_cooking_verbs_reward_recipe_language():
    verbs = load_cooking_verbs()
    assert "saute" in verbs
    rich = _rec(
        title="Chop, saute, stir, and simmer",
        description="Whisk, fold, then bake and rest.",
        recipe_steps=["Blanch tomatoes.", "Peel, dice, mince."],
    )
    poor = _rec(title="A day at the beach", description="Sun and waves.")
    assert score_cooking_verbs(rich) >= 0.9
    assert score_cooking_verbs(poor) == 0.0


def test_shot_density_from_metadata_none_when_missing_signals():
    assert score_shot_density_from_metadata(_rec()) is None
    good = _rec(duration_s=300, recipe_steps=["a", "b", "c", "d", "e"])
    assert score_shot_density_from_metadata(good) == 1.0
    choppy = _rec(duration_s=60, recipe_steps=[f"step {i}" for i in range(30)])
    assert score_shot_density_from_metadata(choppy) < 0.1


def test_score_record_drops_missing_signals_from_denominator():
    high_metadata = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        width=1920,
        audio_present=True,
        description="Chop, saute, and simmer for 12 minutes." * 5,
        recipe_steps=["Chop", "Saute", "Simmer", "Fold", "Rest"],
    )
    no_shape = _rec(license=License.CC_BY, duration_s=300.0, height=1080, description="hi")
    # Missing width -> aspect_ratio None -> weight not counted in denominator.
    experimental_high = score_record(high_metadata, weights=WEIGHTS_EXPERIMENTAL)
    experimental_low = score_record(no_shape, weights=WEIGHTS_EXPERIMENTAL)
    assert experimental_high > experimental_low
    assert 0.0 <= experimental_low <= 1.0


def test_ab_test_prefers_experimental_for_procedural_records():
    procedural = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        width=1920,
        audio_present=True,
        description="Chop, saute, fold, stir, simmer, rest for 5 minutes.",
        recipe_steps=["Chop onion", "Saute onion", "Add stock", "Simmer 20 min", "Rest 5 min"],
    )
    highlight_reel = _rec(
        license=License.CC_BY,
        duration_s=45.0,
        height=1080,
        width=608,
        audio_present=False,
    )
    scored_baseline = score_records([procedural, highlight_reel], weights=WEIGHTS)
    scored_exp = score_records([procedural, highlight_reel], weights=WEIGHTS_EXPERIMENTAL)
    # Experimental weights should widen the gap between procedural and reel.
    b_gap = (scored_baseline[0].quality_score or 0.0) - (scored_baseline[1].quality_score or 0.0)
    e_gap = (scored_exp[0].quality_score or 0.0) - (scored_exp[1].quality_score or 0.0)
    assert e_gap > b_gap
