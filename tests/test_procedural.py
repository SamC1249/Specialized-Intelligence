from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.procedural import (
    PROFILES,
    score_procedural_density,
    score_record_v2,
    score_records_with_profile,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    title: str, description: str = "", steps: list[str] | None = None, lic: License = License.CC_BY
) -> VideoRecord:
    return VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/a",
        title=title,
        description=description,
        recipe_steps=steps or [],
        license=lic,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query="q"),
    )


def test_procedural_zero_for_empty_text():
    r = _rec("")
    assert score_procedural_density(r) == 0.0


def test_procedural_high_for_step_dense_recipe():
    r = _rec(
        "Homemade carbonara",
        "Chop guanciale. Boil pasta in salted water for 8 minutes.",
        steps=[
            "Heat 2 tbsp olive oil in a pan.",
            "Add 100 g of pancetta and cook for 3 minutes.",
            "Whisk 2 eggs with 50 g of grated pecorino.",
            "Drain pasta reserving 1/2 cup of pasta water.",
            "Toss pasta with pancetta, remove from heat.",
            "Add egg mixture, stir vigorously.",
            "Season with black pepper. Serve immediately.",
            "Garnish with more pecorino.",
        ],
    )
    assert score_procedural_density(r) >= 0.6


def test_procedural_low_for_chatty_video():
    r = _rec("A day in the life", "Today we talk about food memories and family stories.")
    assert score_procedural_density(r) < 0.2


def test_v2_dominates_v1_on_procedurally_dense_record():
    dense = _rec(
        "Béchamel",
        "Melt butter, whisk in flour, add milk. Cook for 5 minutes.",
        steps=["Melt 30 g butter", "Whisk in 30 g flour", "Add 500 ml warm milk"],
    )
    v1_score = PROFILES["v1"](dense)
    v2_score = score_record_v2(dense)
    assert v2_score >= v1_score * 0.9


def test_scorer_profile_registry_and_apply():
    r = _rec("Cooking basics", "Chop, stir, boil.", steps=["Do the thing"])
    scored = score_records_with_profile([r], "v2_procedural")
    assert len(scored) == 1
    assert scored[0].quality_score is not None
    assert 0.0 <= scored[0].quality_score <= 1.0


def test_unknown_profile_raises():
    import pytest

    with pytest.raises(KeyError):
        score_records_with_profile([], "does_not_exist")
