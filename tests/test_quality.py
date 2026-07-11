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


def test_action_verbs_boost_score():
    procedural = _rec(
        title="How to chop garlic, dice onions and sauté",
        description="First we chop, then we dice, then we simmer, then we whisk, then we fold, "
        "then we deglaze the pan and reduce the sauce.",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    monologue = _rec(
        title="A philosophical essay about food",
        description="This is a long meditation on ingredients and their meaning. " * 10,
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    assert score_record(procedural) > score_record(monologue)


def test_blocklisted_title_zeros_action_density():
    trailer = _rec(
        title="Chef Trailer - chop, dice, sauté, simmer, whisk, fold",
        description="chop dice sauté simmer whisk fold reduce",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    procedural = _rec(
        title="Chef Technique - chop, dice, sauté, simmer, whisk, fold",
        description="chop dice sauté simmer whisk fold reduce",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    assert score_record(trailer) < score_record(procedural)


def test_domain_swap_changes_verb_relevance():
    # A surgery-relevant record should score higher against the surgery
    # domain than against the cooking domain.
    r = _rec(
        title="Laparoscopic incision and suture technique",
        description="First we incise, then we clamp, then we suture, then we ligate the vessel.",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    assert score_record(r, domain="surgery") > score_record(r, domain="cooking")
