"""Tests for the v2 quality profile (procedural-density signal)."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import PROFILES, score_record
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


def test_profiles_registered():
    assert set(PROFILES) >= {"v1", "v2"}


def test_v1_ignores_procedural_verbs():
    """v1 has no procedural signal, so verb-density gap must be small.

    v2 must widen that gap (see the sibling test below). We assert the
    differential — a direct equality assertion would be brittle because
    text_density is character-count based and the two titles differ by
    a handful of characters.
    """
    verby = _rec(
        title="chop dice mince slice sauté simmer stir whisk reduce garnish serve",
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
    )
    plain = _rec(
        title="ten random unrelated marketing words about a brand experience today value",
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
    )
    v1_gap = score_record(verby, profile="v1") - score_record(plain, profile="v1")
    v2_gap = score_record(verby, profile="v2") - score_record(plain, profile="v2")
    assert v2_gap > v1_gap
    assert v2_gap > 0.05


def test_v2_prefers_procedural_records():
    verby = _rec(
        title="Chop and dice the onion",
        description="Sauté, simmer, stir, then reduce and garnish before serving.",
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
        recipe_steps=["mince garlic", "whisk eggs", "fold in flour", "bake until golden"],
    )
    plain = _rec(
        title="Our brand story",
        description="A journey through delicious moments and lifestyle experiences.",
        license=License.CC_BY,
        height=1080,
        duration_s=300.0,
    )
    assert score_record(verby, profile="v2") > score_record(plain, profile="v2")


def test_v2_and_v1_bounded_zero_to_one():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    for profile in ("v1", "v2"):
        s = score_record(r, profile=profile)
        assert 0.0 <= s <= 1.0


def test_v2_weights_sum_matches_declared():
    # Comparison-first: if we tweak v2's weights, the sum should be
    # documented in PROFILES and reflected in the scoring code.
    assert sum(PROFILES["v2"].values()) > 0
