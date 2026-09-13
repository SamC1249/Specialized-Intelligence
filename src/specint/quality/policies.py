"""Named quality-scoring policies.

A `QualityPolicy` is a small dataclass wrapping a weight vector over the
scoring components exposed by `specint.quality.metrics`. It lets us sweep
multiple weightings over the same corpus and report a Pareto frontier
instead of pretending a single scalar is universally right.

Adding a policy:
  1. Add an entry to `POLICIES` with a rationale in the docstring below.
  2. Make sure every weight refers to a component name registered in
     `specint.quality.metrics._COMPONENTS` — the loader validates this.
  3. Add coverage in `tests/test_policies.py`.

Policies included today:
  - `baseline`         : matches the pre-policy hand weights so old
                         reports stay reproducible.
  - `procedural-heavy` : shifts weight to procedural density; use when
                         downstream training cares about step-following.
  - `license-strict`   : license-clean acts as a near-hard gate; use when
                         a downstream corpus must not include UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QualityPolicy:
    name: str
    weights: dict[str, float] = field(default_factory=dict)
    notes: str = ""

    def normalized(self) -> dict[str, float]:
        total = sum(self.weights.values())
        if total <= 0:
            return dict(self.weights)
        return {k: v / total for k, v in self.weights.items()}


BASELINE = QualityPolicy(
    name="baseline",
    weights={
        "license_clean": 0.35,
        "duration": 0.15,
        "resolution": 0.20,
        "text_density": 0.15,
        "has_steps": 0.15,
    },
    notes="Matches the 2026-06-20 hand weights; do not change without a sweep report.",
)

PROCEDURAL_HEAVY = QualityPolicy(
    name="procedural-heavy",
    weights={
        "license_clean": 0.30,
        "duration": 0.10,
        "resolution": 0.10,
        "text_density": 0.05,
        "has_steps": 0.10,
        "procedural_density": 0.35,
    },
    notes="Weights procedural density highest; test bed for step-following training corpora.",
)

LICENSE_STRICT = QualityPolicy(
    name="license-strict",
    weights={
        "license_clean": 0.70,
        "duration": 0.05,
        "resolution": 0.05,
        "text_density": 0.05,
        "has_steps": 0.05,
        "procedural_density": 0.10,
    },
    notes="License-clean is a near-hard gate; safer for corpora that must exclude UNKNOWN.",
)


POLICIES: dict[str, QualityPolicy] = {
    p.name: p for p in (BASELINE, PROCEDURAL_HEAVY, LICENSE_STRICT)
}


def get_policy(name: str) -> QualityPolicy:
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise KeyError(f"unknown quality policy {name!r}; known={sorted(POLICIES)}") from exc


def list_policies() -> list[str]:
    return sorted(POLICIES)
