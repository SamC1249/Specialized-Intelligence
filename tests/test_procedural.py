"""Procedural-density signal tests."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.procedural import imperative_hits, procedural_density
from specint.records import License, Provenance, VideoRecord


def _rec(title: str = "", description: str = "", steps: list[str] | None = None) -> VideoRecord:
    return VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/x",
        title=title,
        description=description,
        recipe_steps=steps or [],
        license=License.CC0,
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        provenance=Provenance(extractor="tests.test_procedural"),
    )


def test_imperative_hits_counts_basic_verbs() -> None:
    assert imperative_hits("Add garlic and stir until fragrant.") == 2
    assert imperative_hits("") == 0


def test_density_zero_for_non_procedural_text() -> None:
    r = _rec(title="A photo essay about tomatoes in Tuscan sunlight.")
    assert procedural_density(r) == 0.0


def test_density_full_for_dense_recipe_steps() -> None:
    r = _rec(
        title="Pasta",
        description="",
        steps=[
            "Boil pasta.",
            "Stir butter.",
            "Add garlic.",
            "Mix sauce.",
            "Serve warm.",
        ],
    )
    assert procedural_density(r) == 1.0


def test_density_scales_between_zero_and_one() -> None:
    r = _rec(
        description=(
            "This is a long essay about the history of pasta in southern Italy. "
            "There is a lot of context here with very few actual steps. "
            "At one point you simmer the sauce for twenty minutes."
        )
    )
    d = procedural_density(r)
    assert 0.0 < d < 1.0
