from datetime import UTC, datetime

from specint.quality.metrics import procedural_density_raw, score_record
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking video",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_procedural_density_zero_on_empty():
    assert procedural_density_raw("") == 0.0


def test_procedural_density_rewards_imperatives_and_quantities():
    marketing = "Watch this amazing viral cooking video everyone loves so much wow"
    procedural = (
        "chop 2 cups of onion, saute 5 minutes, add 300 g of tomato, simmer 20 minutes, serve"
    )
    assert procedural_density_raw(procedural) > procedural_density_raw(marketing)


def test_procedural_density_capped_at_one():
    dense = " ".join(["chop 2 g add 3 g stir 5 min"] * 20)
    assert procedural_density_raw(dense) <= 1.0


def test_deduplicated_recipe_steps_do_not_double_count():
    rec_dupe = _rec(
        title="Bread",
        description="",
        recipe_steps=["knead the dough for 10 minutes"] * 6,
    )
    rec_unique = _rec(
        title="Bread",
        description="",
        recipe_steps=[
            "knead the dough for 10 minutes",
            "let the dough rise for 60 minutes",
            "bake at 220 degrees for 30 minutes",
        ],
    )
    assert score_record(rec_unique) >= score_record(rec_dupe)


def test_procedural_component_boosts_procedural_records_over_prose():
    prose = _rec(
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
        description="This is a beautiful cinematic cooking film about family memories" * 3,
    )
    procedural = _rec(
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
        description=(
            "Chop 3 onions. Saute 5 minutes. Add 200 g of tomato. Simmer 10 minutes. "
            "Season with salt. Serve hot."
        ),
        recipe_steps=[
            "chop 3 onions",
            "saute 5 minutes",
            "add 200 g tomato",
            "simmer 10 minutes",
        ],
    )
    assert score_record(procedural) > score_record(prose)
