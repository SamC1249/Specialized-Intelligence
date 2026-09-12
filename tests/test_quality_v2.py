from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import SCORERS, score_record, score_record_v2
from specint.quality.metrics_v2 import (
    WEIGHTS_V2,
    _score_language_signal,
    _score_procedural_density,
    component_breakdown,
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


def test_scorers_registry_has_v1_and_v2():
    assert set(SCORERS) >= {"v1", "v2"}


def test_v2_weights_sum_to_one():
    assert abs(sum(WEIGHTS_V2.values()) - 1.0) < 1e-9


def test_v2_returns_value_in_unit_interval():
    r = _rec()
    s = score_record_v2(r)
    assert 0.0 <= s <= 1.0


def test_procedural_density_rewards_step_verbs():
    demonstrator = _rec(
        title="Chop the onion, saute in butter, then simmer with tomato",
        description="We chop, saute, deglaze, and simmer. Then we serve.",
        recipe_steps=["chop the onion", "saute in butter", "simmer with tomato"],
    )
    vlog = _rec(
        title="A day in my life at the beach",
        description="Just vibing. Watching the sunset. Feeling great.",
    )
    assert _score_procedural_density(demonstrator) > _score_procedural_density(vlog)


def test_procedural_density_zero_for_empty_text():
    r = _rec(title="", description="")
    assert _score_procedural_density(r) == 0.0


def test_language_signal_prefers_declared_language():
    with_lang = _rec(language="en", description="A short description with real content")
    without_lang = _rec(description="A short description with real content")
    tiny = _rec(description="")
    assert _score_language_signal(with_lang) > _score_language_signal(without_lang)
    assert _score_language_signal(tiny) == 0.0


def test_v2_dominates_v1_on_procedural_records():
    demonstrator = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        language="en",
        title="How to saute onions",
        description="Heat the pan. Add oil. Add onions. Stir. Season. Serve.",
        recipe_steps=["heat pan", "add oil", "add onions", "stir", "season", "serve"],
    )
    lecture = _rec(
        license=License.CC_BY,
        duration_s=2400.0,
        height=1080,
        language="en",
        title="A lecture on culinary history",
        description="An academic overview of food history in the 19th century.",
    )
    v2_gap = score_record_v2(demonstrator) - score_record_v2(lecture)
    v1_gap = score_record(demonstrator) - score_record(lecture)
    assert v2_gap > v1_gap


def test_component_breakdown_reports_all_components_and_final():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    parts = component_breakdown(r)
    for name in WEIGHTS_V2:
        assert name in parts
        assert 0.0 <= parts[name] <= 1.0
    assert 0.0 <= parts["__final__"] <= 1.0
