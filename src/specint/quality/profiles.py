"""Named scoring profiles.

The seed `metrics.py` has one hardcoded weight vector. That is fine for
a first baseline but blocks A/B comparisons — a profile is data, not
code, so future PRs can add or edit one without touching the scorer.

Every profile is a mapping `component_name -> weight`. Component names
must be registered in `metrics._COMPONENTS`. Weights are normalized at
score-time so they need not sum to 1.

Rules:
  * `baseline` must never be edited. It is the frozen reference for
    `reports/baseline-2026-06-20.json`.
  * Adding a profile requires adding a benchmark row under `reports/`
    per AGENTS.md "Comparison-First Rule".
"""

from __future__ import annotations

from collections.abc import Mapping

Profile = Mapping[str, float]


BASELINE: Profile = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.15,
    "has_steps": 0.15,
}


COOKING: Profile = {
    "license_clean": 0.30,
    "duration": 0.12,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.13,
    "relevance": 0.20,
}


PROFILES: dict[str, Profile] = {
    "baseline": BASELINE,
    "cooking": COOKING,
}


def get_profile(name: str) -> Profile:
    if name not in PROFILES:
        raise KeyError(f"unknown scoring profile: {name!r} (known: {sorted(PROFILES)})")
    return PROFILES[name]
