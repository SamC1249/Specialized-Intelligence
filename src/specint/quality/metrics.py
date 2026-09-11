"""Metadata-only quality scoring with selectable weight profiles.

Each scoring component returns a value in [0, 1]; the final score is a
weighted sum, also in [0, 1]. Scoring is deliberately *metadata-only* so
we can rank a backlog of millions of candidates before deciding which to
actually download.

Profiles (comparison-first):
  - `v1` (baseline, ships in `reports/baseline-2026-06-20.json`):
       license 0.35, duration 0.15, resolution 0.20, text_density 0.15,
       has_steps 0.15.
  - `v2` (2026-09-11, adds procedural-density signal):
       license 0.30, duration 0.10, resolution 0.15, text_density 0.10,
       has_steps 0.15, procedural_density 0.20.
       Rewards records whose title/description/steps read like a
       procedural cooking transcript, not marketing copy.

Components:
  - license_clean       : 1 if license is redistributable, else 0.
  - duration            : peaks at 5 minutes (procedural sweet spot),
                          penalizes very short and very long.
  - resolution          : >=720p ramps from 0 to 1.
  - text_density        : combined length of title + description + steps.
  - has_steps           : 1 if recipe_steps non-empty.
  - procedural_density  : cooking-verb hits per 100 words across
                          title + description + step text.

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `_COMPONENTS` and to every profile in `PROFILES` with a
     documented rationale (or set weight 0 to keep it inactive there).
  3. Update tests in `tests/test_quality.py` / `tests/test_quality_v2.py`
     with the new lower/upper bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from specint.records import VideoRecord

Profile = Literal["v1", "v2"]

PROFILES: dict[str, dict[str, float]] = {
    "v1": {
        "license_clean": 0.35,
        "duration": 0.15,
        "resolution": 0.20,
        "text_density": 0.15,
        "has_steps": 0.15,
        "procedural_density": 0.0,
    },
    "v2": {
        "license_clean": 0.30,
        "duration": 0.10,
        "resolution": 0.15,
        "text_density": 0.10,
        "has_steps": 0.15,
        "procedural_density": 0.20,
    },
}

# Backwards-compat alias: `WEIGHTS` used to be the only knob. Keep it
# pointing at the v1 profile so any downstream import still works.
WEIGHTS: dict[str, float] = PROFILES["v1"]

# English cooking-verb allowlist. Kept short on purpose: the goal is a
# high-precision signal, not a full lexicon. Multilingual expansion is a
# follow-up (see docs/plan-2026-09-11.md).
COOKING_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "caramelize",
        "chill",
        "chop",
        "combine",
        "cook",
        "cool",
        "cover",
        "cream",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "drizzle",
        "fold",
        "fry",
        "garnish",
        "glaze",
        "grate",
        "grease",
        "grill",
        "heat",
        "juice",
        "knead",
        "layer",
        "marinate",
        "mash",
        "measure",
        "melt",
        "mince",
        "mix",
        "peel",
        "poach",
        "pour",
        "preheat",
        "press",
        "puree",
        "reduce",
        "rest",
        "roast",
        "roll",
        "saute",
        "sautee",
        "sauté",
        "scoop",
        "sear",
        "season",
        "serve",
        "sift",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stew",
        "stir",
        "strain",
        "temper",
        "toast",
        "toss",
        "warm",
        "whisk",
        "whip",
    }
)

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


def _score_license(record: VideoRecord) -> float:
    return 1.0 if record.license.is_redistributable else 0.0


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None or d <= 0:
        return 0.0
    target = 300.0  # 5 minutes
    if d <= target:
        return d / target
    return max(0.0, 1.0 - (d - target) / (target * 12))  # decays out to ~1 hour


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


def _procedural_corpus(record: VideoRecord) -> list[str]:
    parts: list[str] = [record.title, record.description, *record.recipe_steps]
    text = " ".join(p for p in parts if p)
    return _WORD_RE.findall(text.lower())


def _score_procedural_density(record: VideoRecord) -> float:
    """Cooking-verb hits per 100 words, saturating at ~5% verb density.

    Rationale: real procedural transcripts hit multiple imperative verbs
    per short paragraph; marketing / channel-branding blurbs almost
    never do. 5% verbs-per-word is a strong signal without being
    achievable through keyword stuffing on titles alone.
    """
    words = _procedural_corpus(record)
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in COOKING_VERBS)
    ratio = hits / len(words)
    return min(1.0, ratio / 0.05)


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
}


def _resolve_profile(profile: Profile | dict[str, float] | None) -> dict[str, float]:
    if profile is None:
        return PROFILES["v1"]
    if isinstance(profile, dict):
        return profile
    if profile not in PROFILES:
        raise ValueError(f"unknown quality profile: {profile!r}; known: {sorted(PROFILES)}")
    return PROFILES[profile]


def score_record(record: VideoRecord, profile: Profile | dict[str, float] | None = None) -> float:
    weights = _resolve_profile(profile)
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.0
    raw = 0.0
    for name, fn in _COMPONENTS.items():
        w = weights.get(name, 0.0)
        if w == 0.0:
            continue
        raw += w * fn(record)
    return raw / total_weight


def score_records(
    records: Iterable[VideoRecord], profile: Profile | dict[str, float] | None = None
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, profile=profile)) for r in records]
