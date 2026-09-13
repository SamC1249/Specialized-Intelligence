"""Unit tests for QualityPolicy loading + scoring integration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from specint.quality import (
    BASELINE,
    COMPONENTS,
    LICENSE_STRICT,
    POLICIES,
    PROCEDURAL_HEAVY,
    QualityPolicy,
    get_policy,
    list_policies,
    score_record,
)
from specint.records import License, Provenance, VideoRecord


def _rec(license: License = License.CC_BY, height: int | None = 1080) -> VideoRecord:
    return VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/1",
        title="Pasta",
        description="Chop, mix, stir.",
        duration_s=300,
        height=height,
        license=license,
        recipe_steps=["Chop.", "Mix.", "Stir."],
        provenance=Provenance(extractor="tests", fetched_at=datetime(2026, 9, 13, tzinfo=UTC)),
    )


class TestRegistry:
    def test_baseline_registered(self):
        assert "baseline" in list_policies()
        assert get_policy("baseline") is BASELINE

    def test_all_policies_have_notes(self):
        for name in list_policies():
            assert POLICIES[name].notes, f"policy {name} missing notes"

    def test_unknown_policy_raises(self):
        with pytest.raises(KeyError):
            get_policy("does-not-exist")


class TestWeightsReferValidComponents:
    @pytest.mark.parametrize("name", ["baseline", "procedural-heavy", "license-strict"])
    def test_component_names_are_registered(self, name):
        for component in POLICIES[name].weights:
            assert component in COMPONENTS, f"policy {name} refs unknown component {component}"


class TestPolicyChangesScore:
    def test_baseline_matches_legacy_hand_weights(self):
        legacy_weights = {
            "license_clean": 0.35,
            "duration": 0.15,
            "resolution": 0.20,
            "text_density": 0.15,
            "has_steps": 0.15,
        }
        assert BASELINE.weights == legacy_weights

    def test_license_strict_penalises_unknown_more(self):
        clean = _rec(license=License.CC_BY)
        dirty = _rec(license=License.UNKNOWN)

        base_gap = score_record(clean, BASELINE) - score_record(dirty, BASELINE)
        strict_gap = score_record(clean, LICENSE_STRICT) - score_record(dirty, LICENSE_STRICT)

        assert strict_gap > base_gap

    def test_procedural_heavy_boosts_stepful_records(self):
        stepful = _rec()
        stepless = _rec()
        stepless = stepless.model_copy(update={"recipe_steps": []})

        base_gap = score_record(stepful, BASELINE) - score_record(stepless, BASELINE)
        proc_gap = score_record(stepful, PROCEDURAL_HEAVY) - score_record(
            stepless, PROCEDURAL_HEAVY
        )
        assert proc_gap > base_gap


class TestPolicyValidation:
    def test_unknown_component_raises(self):
        bad = QualityPolicy(name="bad", weights={"nonexistent": 1.0}, notes="test")
        with pytest.raises(KeyError):
            score_record(_rec(), bad)

    def test_zero_weight_policy_is_zero(self):
        empty = QualityPolicy(name="empty", weights={}, notes="test")
        assert score_record(_rec(), empty) == 0.0
