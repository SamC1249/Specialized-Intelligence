from datetime import UTC, datetime

from specint.quality import score_record, score_records
from specint.quality.metrics import (
    _count_cooking_verbs,
    _count_measurements,
    _score_procedural_density,
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
        recipe_steps=["chop", "saute", "deglaze"],
    )
    assert score_record(rich) > score_record(bare)
    assert score_record(rich) > 0.7


def test_score_records_attaches_quality():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [scored] = score_records([r])
    assert scored.quality_score is not None
    assert 0.0 <= scored.quality_score <= 1.0


def test_cooking_verb_and_measurement_counters():
    text = "Chop the onion, simmer 10 minutes, add 200 g flour, whisk, and fold the batter."
    assert _count_cooking_verbs(text) >= 4
    assert _count_measurements(text) >= 2


def test_procedural_density_is_graded_not_binary():
    base = _rec(recipe_steps=["add salt"])
    richer = _rec(
        recipe_steps=[
            "Preheat oven to 400°F.",
            "Chop 2 onions and mince 3 garlic cloves.",
            "Saute aromatics in 2 tbsp butter for 5 minutes.",
            "Add 1 cup stock and simmer 15 minutes.",
            "Whisk 2 eggs with 100 g cream.",
            "Fold eggs into pan and bake 20 minutes.",
        ],
        description="A 30-minute weeknight dish with simmering and baking.",
    )
    low = _score_procedural_density(base)
    high = _score_procedural_density(richer)
    assert 0.0 <= low < 0.5
    assert high > low
    assert 0.0 <= high <= 1.0


def test_procedural_density_rewards_free_text_without_steps():
    r = _rec(
        description=(
            "Chop 1 onion, saute in 2 tbsp butter 5 minutes, "
            "simmer with 200 g tomato for 10 minutes, season, and fold in basil."
        ),
    )
    assert _score_procedural_density(r) > 0.0
