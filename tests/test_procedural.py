"""Unit tests for the procedural-density scorer."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.procedural import (
    IMPERATIVE_VERBS,
    count_verb_hits,
    procedural_density_score,
    verb_hits_per_second,
    verb_hits_per_step,
)
from specint.records import License, Provenance, VideoRecord


def _prov() -> Provenance:
    return Provenance(extractor="tests", fetched_at=datetime(2026, 9, 13, tzinfo=UTC))


def _rec(
    *,
    title: str = "",
    description: str = "",
    steps: list[str] | None = None,
    duration_s: float | None = None,
    license: License = License.CC_BY,
) -> VideoRecord:
    return VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/1",
        title=title,
        description=description,
        recipe_steps=list(steps or []),
        duration_s=duration_s,
        license=license,
        provenance=_prov(),
    )


class TestCountVerbHits:
    def test_empty_text(self):
        assert count_verb_hits("") == 0

    def test_hits_bare_verbs(self):
        assert count_verb_hits("chop mix stir") == 3

    def test_case_insensitive(self):
        assert count_verb_hits("Chop the onions and Mix them.") == 2

    def test_ing_and_ed_variants(self):
        assert count_verb_hits("chopping the onions, mixed carefully") == 2

    def test_ignores_unknown_words(self):
        assert count_verb_hits("meanwhile ponder philosophy") == 0

    def test_lexicon_is_lower_case(self):
        assert all(v == v.lower() for v in IMPERATIVE_VERBS)


class TestVerbHitsPerStep:
    def test_with_steps(self):
        rec = _rec(
            title="Pasta",
            steps=["Chop the onions.", "Mix flour.", "Stir the sauce."],
        )
        val = verb_hits_per_step(rec)
        assert 0.9 <= val <= 1.5

    def test_without_steps_falls_back_to_description(self):
        rec = _rec(description="Chop, mix, stir, fold, bake, boil.")
        assert verb_hits_per_step(rec) > 0

    def test_empty_record(self):
        assert verb_hits_per_step(_rec()) == 0.0


class TestVerbHitsPerSecond:
    def test_needs_duration(self):
        rec = _rec(description="chop mix stir")
        assert verb_hits_per_second(rec) == 0.0

    def test_scales_with_duration(self):
        short = _rec(description="chop mix stir", duration_s=60)
        long = _rec(description="chop mix stir", duration_s=600)
        assert verb_hits_per_second(short) > verb_hits_per_second(long)


class TestProceduralDensityScore:
    def test_bounds(self):
        assert 0.0 <= procedural_density_score(_rec()) <= 1.0

    def test_high_density(self):
        rec = _rec(
            title="Pasta carbonara",
            description="Chop, mix, stir, fold, whisk.",
            steps=[
                "Chop onions.",
                "Whisk eggs.",
                "Mix in cheese.",
                "Stir into pasta.",
            ],
            duration_s=300,
        )
        assert procedural_density_score(rec) >= 0.5

    def test_low_density(self):
        rec = _rec(
            title="A quiet countryside afternoon",
            description="Beautiful shots of the countryside without narration.",
            duration_s=300,
        )
        assert procedural_density_score(rec) < 0.2

    def test_missing_duration_only_uses_step_component(self):
        rec = _rec(
            steps=["Chop onions.", "Mix flour.", "Stir sauce.", "Bake."],
        )
        assert procedural_density_score(rec) > 0.0
