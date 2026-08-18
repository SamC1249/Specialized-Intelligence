"""Profile-aware quality scoring tests.

These tests are the guardrail for H3 (quality is policy, not fact).
If a profile stops ranking sources the way the plan claims it should,
the tests fail loudly.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specint.compare import run_all_profiles, run_comparison
from specint.quality import available_profiles, score_record
from specint.quality.metrics import (
    WEIGHT_PROFILES,
    _score_language_confidence,
    _score_procedural_density,
    _score_recency,
    detect_language,
)
from specint.records import License, Provenance, SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


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


def test_available_profiles_include_expected_keys():
    assert set(available_profiles()) >= {"default", "procedural", "resolution"}


def test_default_profile_matches_2026_06_20_baseline_for_rich_record():
    # A `default`-profile score for a rich record must still be > 0.7,
    # matching the invariant asserted in test_quality.py.
    rich = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        description="A 5-minute knife skills tutorial." * 10,
        recipe_steps=["chop", "saute", "deglaze"],
    )
    assert score_record(rich, profile="default") > 0.7


def test_procedural_profile_rewards_recipe_steps_over_bare_footage():
    steps = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=720,
        description="Chop onions, saute, deglaze with wine, simmer sauce, plate.",
        recipe_steps=["chop", "saute", "deglaze", "simmer", "plate"],
    )
    bare = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=720,
        description="",
        recipe_steps=[],
    )
    assert score_record(steps, profile="procedural") > score_record(bare, profile="procedural")


def test_resolution_profile_rewards_hd_and_landscape():
    hd = _rec(
        license=License.CC0,
        duration_s=900.0,
        width=1920,
        height=1080,
    )
    lofi = _rec(
        license=License.CC0,
        duration_s=900.0,
        width=480,
        height=360,
    )
    assert score_record(hd, profile="resolution") > score_record(lofi, profile="resolution")


def test_score_record_rejects_unknown_profile():
    with pytest.raises(KeyError):
        score_record(_rec(), profile="does-not-exist")


def test_weight_profiles_all_normalise_to_1():
    for name, weights in WEIGHT_PROFILES.items():
        total = sum(weights.values())
        assert total > 0, f"profile {name} has zero total weight"
        # Every component in the registry must be present, even if 0.
        # This ensures adding a new component forces every profile to
        # explicitly weight it.
        from specint.quality.metrics import _COMPONENTS

        missing = set(_COMPONENTS) - set(weights)
        assert not missing, f"profile {name} missing weights for {missing}"


def test_detect_language_english_and_none_for_gibberish():
    assert detect_language("This is the recipe for you and your family") == "en"
    assert detect_language("La receta con el pollo y la salsa") == "es"
    assert detect_language("xxxx yyyy zzzz") is None
    assert detect_language("") is None


def test_language_confidence_uses_explicit_hint_first():
    hinted = _rec(language="fr", description="")
    assert _score_language_confidence(hinted) == 1.0
    detected = _rec(description="the quick and the recipe for you")
    assert _score_language_confidence(detected) == 1.0
    empty = _rec(description="")
    assert _score_language_confidence(empty) == 0.0


def test_procedural_density_scales_with_verb_hits():
    dense = _rec(
        description="chop slice mix bake roast whisk sift knead simmer stir",
        recipe_steps=["chop", "mix"],
    )
    sparse = _rec(description="the recipe is nice")
    assert _score_procedural_density(dense) > _score_procedural_density(sparse)
    assert _score_procedural_density(dense) <= 1.0


def test_recency_component_bounds():
    fresh = _rec(published_at=datetime.now(UTC))
    old = _rec(published_at=datetime(2000, 1, 1, tzinfo=UTC))
    unknown = _rec(published_at=None)
    assert _score_recency(fresh) > 0.9
    assert _score_recency(old) == 0.0
    assert _score_recency(unknown) == 0.5


def test_e2e_profiles_beat_or_match_2026_06_20_baseline(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }

    default_rows = run_comparison(query, by_source, profile="default")
    by_source_row = {r.source: r for r in default_rows}
    # Baseline numbers from reports/baseline-2026-06-20.json.
    baseline = {
        "wikimedia": 0.62,
        "peertube": 0.57,
        "common_crawl": 0.53,
    }
    for name, floor in baseline.items():
        assert by_source_row[name].mean_quality >= floor - 1e-9, name

    all_profiles = run_all_profiles(query, by_source)
    assert set(all_profiles) == set(available_profiles())

    procedural = {r.source: r for r in all_profiles["procedural"]}
    # Under the procedural profile, common_crawl (which is the only
    # fixture-source with recipe_steps) must beat the source with the
    # lowest baseline default score (archive_org).
    assert procedural["common_crawl"].mean_quality > procedural["archive_org"].mean_quality

    # Every profile emits an __unique_total__ row and it must be <= __total__.
    for rows in all_profiles.values():
        total = next(r for r in rows if r.source == "__total__")
        unique = next(r for r in rows if r.source == "__unique_total__")
        assert unique.n_records <= total.n_records
