from datetime import UTC, datetime

from specint.quality import score_record, score_records
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


def test_procedural_density_beats_has_steps_for_richer_recipes():
    from specint.quality.metrics import ALL_COMPONENTS

    proc = ALL_COMPONENTS["procedural_density"]
    thin = _rec(recipe_steps=["prep", "cook", "serve"])
    thick = _rec(
        title="Chop, dice, saute, simmer, whisk and fold",
        recipe_steps=[
            "chop garlic",
            "dice onion",
            "saute in oil",
            "simmer for 20 minutes",
            "whisk eggs",
            "fold in flour",
            "bake at 200",
            "rest before serving",
        ],
    )
    assert proc(thick) > proc(thin)
    assert proc(thick) == 1.0


def test_cooking_relevance_multilingual():
    from specint.quality.metrics import ALL_COMPONENTS

    rel = ALL_COMPONENTS["cooking_relevance"]
    english = _rec(title="Homemade sourdough bread recipe", description="")
    spanish = _rec(title="Sofrito de ajo y cebolla receta", description="cocina rapida")
    assert rel(english) > 0
    assert rel(spanish) > 0


def test_custom_weights_override_defaults():
    r_license_only = _rec(license=License.CC0)
    from specint.quality.metrics import score_record

    assert score_record(r_license_only, weights={"license_clean": 1.0}) == 1.0
    assert score_record(r_license_only, weights={"resolution": 1.0}) == 0.0
