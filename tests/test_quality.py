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


def test_procedural_density_rewards_verbs_and_steps():
    lean = _rec(license=License.CC_BY, duration_s=300.0, height=1080, description="family dinner")
    dense = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        description=(
            "Chop the onion, saute for 5 minutes, add tomatoes, simmer 20 minutes at 180 C, "
            "season, serve. Preheat oven to 350 F. Slice, dice, mince."
        ),
        recipe_steps=[
            "chop onion",
            "saute for 5 minutes",
            "add tomato",
            "simmer 20 minutes",
            "season",
            "serve",
            "slice bread",
            "toast",
        ],
    )
    assert score_record(dense) > score_record(lean)


def test_procedural_density_bounded_zero_one():
    empty = _rec(license=License.CC_BY)
    assert 0.0 <= score_record(empty) <= 1.0
    maxed = _rec(
        license=License.CC0,
        duration_s=300.0,
        height=1080,
        description=" ".join(sorted({"chop", "saute", "boil", "simmer", "roast", "reduce"}))
        + " 350 F 180 C 20 minutes 5 minutes 30 seconds",
        recipe_steps=[f"step {i}" for i in range(10)],
    )
    s = score_record(maxed)
    assert 0.0 <= s <= 1.0


def test_procedural_density_reranks_over_bare_resolution():
    # Two records tied on license+duration+resolution: the procedurally denser
    # one must score strictly higher. This locks in the WorldPrediction-inspired
    # reranking rationale documented in docs/artifacts/2025-worldprediction.md.
    a = _rec(license=License.CC_BY, duration_s=240.0, height=1080, description="a")
    b = _rec(
        license=License.CC_BY,
        duration_s=240.0,
        height=1080,
        description="chop saute simmer for 10 minutes at 180 C",
        recipe_steps=["chop", "saute", "simmer"],
    )
    assert score_record(b) > score_record(a)
