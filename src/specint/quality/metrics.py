"""Metadata-only quality scoring.

Every component returns a value in [0, 1]; the final score is a weighted
sum, also in [0, 1]. Scoring is deliberately *metadata-only* so we can
rank a backlog of millions of candidates before deciding which to
actually download.

There are two scorers now:

- `score_record_v1` — the seed scorer from 2026-06-20. Kept verbatim for
  benchmark continuity (ablation and Kendall-τ comparisons).
- `score_record_v2` — the current default. Adds:
    * `license_tier`: CC0/PD > CC-BY > CC-BY-SA > OTHER_FREE > UNKNOWN
      > RESTRICTED, so UNKNOWN no longer collapses to zero but is
      clearly penalised. This kills the "unknown-license page beats a
      CC-BY-SA video" pathology we saw in the 2026-06-20 baseline.
    * `procedural_density`: domain-aware verb count over
      title + description + recipe_steps. Uses the domain's
      `procedural_verbs` list from `specint.domains`. Defaults to
      cooking.

`score_records` and `score_record` route to v2. Ablation and tests can
call the v1 functions directly.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `WEIGHTS_V2` with a documented rationale.
  3. Update tests in `tests/test_quality.py` with the new bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.domains import DEFAULT_DOMAIN, Domain
from specint.records import License, VideoRecord

WEIGHTS_V1: dict[str, float] = {
    "license_clean": 0.35,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.15,
    "has_steps": 0.15,
}

WEIGHTS_V2: dict[str, float] = {
    "license_tier": 0.30,
    "duration": 0.15,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_density": 0.20,
}


_LICENSE_TIER_SCORE: dict[License, float] = {
    License.CC0: 1.00,
    License.PUBLIC_DOMAIN: 0.95,
    License.CC_BY: 0.90,
    License.CC_BY_SA: 0.85,
    License.OTHER_FREE: 0.70,
    License.UNKNOWN: 0.25,
    License.RESTRICTED: 0.00,
}


def _score_license_clean(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_license_tier(record: VideoRecord) -> float:
    return _LICENSE_TIER_SCORE.get(record.license, 0.0)


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))


def _score_resolution(record: VideoRecord) -> float:
    h = record.height
    if h is None or h <= 0:
        return 0.0
    if h >= 1080:
        return 1.0
    if h >= 720:
        return 0.8
    if h >= 480:
        return 0.5
    return 0.2


def _score_text_density(record: VideoRecord) -> float:
    chars = len(record.title) + len(record.description)
    chars += sum(len(s) for s in record.recipe_steps)
    if chars <= 0:
        return 0.0
    target = 800.0
    return min(1.0, chars / target)


def _score_has_steps(record: VideoRecord) -> float:
    return 1.0 if record.recipe_steps else 0.0


_WORD_RE = re.compile(r"[a-z][a-z\-]*")


def _score_procedural_density(record: VideoRecord, domain: Domain) -> float:
    corpus = " ".join([record.title, record.description, *record.recipe_steps]).lower()
    tokens = _WORD_RE.findall(corpus)
    if not tokens:
        return 0.0
    verb_set = set(domain.procedural_verbs)
    hits = sum(1 for t in tokens if t in verb_set)
    return min(1.0, hits / 8.0)


_COMPONENTS_V1 = {
    "license_clean": _score_license_clean,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
}


def _weighted(components: dict[str, float], values: dict[str, float]) -> float:
    total_weight = sum(components.values())
    if total_weight <= 0:
        return 0.0
    raw = sum(components[name] * values[name] for name in components)
    return raw / total_weight


def score_record_v1(record: VideoRecord) -> float:
    values = {name: fn(record) for name, fn in _COMPONENTS_V1.items()}
    return _weighted(WEIGHTS_V1, values)


def score_record_v2(
    record: VideoRecord,
    domain: Domain = DEFAULT_DOMAIN,
    weights: dict[str, float] | None = None,
) -> float:
    values = {
        "license_tier": _score_license_tier(record),
        "duration": _score_duration(record),
        "resolution": _score_resolution(record),
        "text_density": _score_text_density(record),
        "has_steps": _score_has_steps(record),
        "procedural_density": _score_procedural_density(record, domain),
    }
    return _weighted(weights or WEIGHTS_V2, values)


def component_values(record: VideoRecord, domain: Domain = DEFAULT_DOMAIN) -> dict[str, float]:
    """Return every v2 component's raw value. Used by the ablation harness."""
    return {
        "license_tier": _score_license_tier(record),
        "license_clean": _score_license_clean(record),
        "duration": _score_duration(record),
        "resolution": _score_resolution(record),
        "text_density": _score_text_density(record),
        "has_steps": _score_has_steps(record),
        "procedural_density": _score_procedural_density(record, domain),
    }


def score_record(record: VideoRecord, domain: Domain = DEFAULT_DOMAIN) -> float:
    return score_record_v2(record, domain=domain)


def score_records(
    records: Iterable[VideoRecord],
    domain: Domain = DEFAULT_DOMAIN,
) -> list[VideoRecord]:
    return [r.with_quality(score_record_v2(r, domain=domain)) for r in records]


WEIGHTS: dict[str, float] = WEIGHTS_V2

__all__ = [
    "WEIGHTS",
    "WEIGHTS_V1",
    "WEIGHTS_V2",
    "component_values",
    "score_record",
    "score_record_v1",
    "score_record_v2",
    "score_records",
]
