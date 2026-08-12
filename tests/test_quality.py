"""Tests for metadata-only quality scoring."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.metrics import (
    WEIGHTS,
    _score_language_match,
    _score_procedural_density,
    score_record,
    score_records,
)
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(**overrides):
    base = {
        "id": "test:1",
        "source": "test",
        "source_native_id": "1",
        "url": "https://example.test/1",
        "title": "Pasta",
        "provenance": Provenance(extractor="test"),
        "license": License.CC_BY,
        "duration_s": 300.0,
        "height": 1080,
    }
    base.update(overrides)
    return VideoRecord(**base)


def test_weights_sum_close_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6


def test_score_in_unit_interval():
    r = _rec()
    s = score_record(r)
    assert 0.0 <= s <= 1.0


def test_license_dominates_when_restricted():
    clean = _rec()
    dirty = _rec(license=License.RESTRICTED)
    assert score_record(clean) > score_record(dirty) + 0.20


def test_score_records_attaches_quality_scores():
    r = _rec()
    scored = score_records([r])
    assert scored[0].quality_score is not None
    assert 0.0 <= scored[0].quality_score <= 1.0


def test_procedural_density_counts_imperatives():
    r = _rec(
        title="How to make pasta",
        description="Boil water, add pasta, stir occasionally, drain and serve.",
    )
    # 4 imperatives (boil/add/stir/drain/serve is 5); serve is in the list
    hits = _score_procedural_density(r)
    assert hits > 0.4
    plain = _rec(title="Pasta", description="A photo.")
    assert _score_procedural_density(plain) == 0.0


def test_language_match_prefers_matching_language():
    r = _rec(title="How to make pasta", description="Boil the water and add pasta.", language="en")
    q_en = SourceQuery(terms=["cooking"], language="en")
    q_es = SourceQuery(terms=["cooking"], language="es")
    assert _score_language_match(r, q_en) == 1.0
    assert _score_language_match(r, q_es) == 0.0


def test_language_match_returns_neutral_when_no_query_language():
    r = _rec(title="How to make pasta", description="Boil the water.", language="en")
    assert _score_language_match(r, SourceQuery(terms=["x"])) == 1.0
    assert _score_language_match(_rec(language=None), SourceQuery(terms=["x"])) == 0.5


def test_scoring_uses_published_at_optional():
    r = _rec(published_at=datetime(2024, 1, 1, tzinfo=UTC))
    assert 0.0 <= score_record(r) <= 1.0


def test_score_bare_record_is_low_relative_to_rich_record():
    bare = _rec(
        title="Video",
        description="",
        license=License.UNKNOWN,
        duration_s=None,
        height=None,
    )
    rich = _rec(
        title="Boil, whisk and simmer: creamy tomato soup recipe",
        description="Melt butter, add onions, stir, pour cream, season and serve." * 3,
        recipe_steps=["Chop onions", "Saute", "Add cream", "Simmer"],
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        language="en",
    )
    assert score_record(bare) < 0.25
    assert score_record(rich) > score_record(bare) + 0.4
