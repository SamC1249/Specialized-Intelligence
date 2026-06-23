from __future__ import annotations

from specint.records import License, Provenance, VideoRecord
from specint.wm_utility import rank_records, wm_utility_score


def _rec(**kw) -> VideoRecord:
    base = {
        "id": "x:1",
        "source": "wikimedia",
        "source_native_id": "1",
        "url": "https://example.org/p",
        "title": "Knife skills: dicing onions",
        "description": "Hand-held footage of slicing technique with audio commentary",
        "license": License.CC_BY,
        "provenance": Provenance(extractor="t"),
        "duration_s": 180.0,
        "height": 1080,
        "recipe_steps": ["1. peel", "2. slice", "3. dice"],
    }
    base.update(kw)
    return VideoRecord(**base)


def test_score_in_unit_interval():
    r = _rec()
    s = wm_utility_score(r, motion_score=0.7)
    assert 0.0 <= s <= 1.0


def test_hand_held_action_clip_beats_static_montage():
    action = _rec(id="action", title="Slicing onion close-up")
    montage = _rec(
        id="mont",
        title="Plated dishes beauty shot",
        description="Slow motion close-up macro food porn ASMR",
        recipe_steps=[],
        height=1080,
        duration_s=60.0,
    )
    s_action = wm_utility_score(action, motion_score=0.8)
    s_montage = wm_utility_score(montage, motion_score=0.02)
    assert s_action > s_montage + 0.1


def test_zero_motion_is_penalised():
    r = _rec()
    high = wm_utility_score(r, motion_score=0.9)
    low = wm_utility_score(r, motion_score=0.0)
    assert high > low


def test_rank_records_orders_by_utility():
    a = _rec(id="a", duration_s=20.0, height=240, recipe_steps=[])
    b = _rec(id="b")
    ranked = rank_records([a, b], motion_scores={"a": 0.1, "b": 0.7})
    assert [r.id for r in ranked] == ["b", "a"]
