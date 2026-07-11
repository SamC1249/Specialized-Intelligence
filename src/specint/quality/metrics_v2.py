"""Quality scorer v2 — adversarial improvements on `metrics.py`.

Design deltas vs. v1 (see `docs/plan-2026-07-11.md`, hypothesis H2):

* **Missing metadata is neutral, not zero.** In v1 a source that never
  populates `width`/`height` (e.g. `archive_org`) was punished as if
  every clip were sub-480p. v2 assigns 0.5 to unknown numeric fields so
  the scorer stops confusing "we don't know" with "we know it's bad".
* **License tier.** All redistributable licenses are equally *legal*,
  but they are not equal in downstream *cost*: attribution burdens
  and share-alike constraints matter when we bake training corpora.
  Order: `CC0 > PD > CC-BY > CC-BY-SA > OTHER_FREE >> UNKNOWN > RESTRICTED`.
* **Procedural verb density.** For world-model training, the value of
  a cooking clip roughly tracks how many state-changing actions it
  describes. We compute a hit rate of a small verb list on
  title+description+recipe_steps (case-folded, whitespace-tokenised).
  This is deliberately a metadata-only proxy — no video download.
* **Text density is bounded and log-scaled.** v1's linear text score
  saturates too easily; a 400-char description is nearly as good as
  a 800-char one. v2 uses `log(1 + chars) / log(1 + target)`.
* **Resolution x fps combo.** Higher fps is worth marginally more for
  procedural learning; when fps is unknown, resolution alone carries.

Public API mirrors v1 (`score_record`, `score_records`) so the
comparison harness can swap them in.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from specint.records import License, VideoRecord

WEIGHTS: dict[str, float] = {
    "license_tier": 0.30,
    "duration": 0.12,
    "resolution": 0.15,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_density": 0.18,
    "language_known": 0.05,
}

LICENSE_TIER: dict[License, float] = {
    License.CC0: 1.00,
    License.PUBLIC_DOMAIN: 0.95,
    License.CC_BY: 0.80,
    License.CC_BY_SA: 0.65,
    License.OTHER_FREE: 0.55,
    License.UNKNOWN: 0.00,
    License.RESTRICTED: 0.00,
}

PROCEDURAL_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
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
        "grill",
        "heat",
        "julienne",
        "knead",
        "marinate",
        "melt",
        "mince",
        "mix",
        "peel",
        "poach",
        "pour",
        "preheat",
        "reduce",
        "rest",
        "roast",
        "roll",
        "saute",
        "sauté",
        "sear",
        "season",
        "serve",
        "shred",
        "sift",
        "simmer",
        "slice",
        "spread",
        "sprinkle",
        "steam",
        "stir",
        "strain",
        "temper",
        "toast",
        "toss",
        "whip",
        "whisk",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")
_TARGET_TEXT_CHARS = 800.0
_TARGET_DURATION_S = 300.0
_DURATION_DECAY_S = 3600.0  # score reaches 0 at ~1h past the target
_NEUTRAL_UNKNOWN = 0.5


def _score_license_tier(record: VideoRecord) -> float:
    return LICENSE_TIER.get(record.license, 0.0)


def _score_duration(record: VideoRecord) -> float:
    d = record.duration_s
    if d is None:
        return _NEUTRAL_UNKNOWN
    if d <= 0:
        return 0.0
    if d <= _TARGET_DURATION_S:
        return d / _TARGET_DURATION_S
    over = d - _TARGET_DURATION_S
    return max(0.0, 1.0 - over / _DURATION_DECAY_S)


def _score_resolution(record: VideoRecord) -> float:
    h = record.height
    if h is None:
        return _NEUTRAL_UNKNOWN
    if h <= 0:
        return 0.0
    if h >= 1080:
        base = 1.0
    elif h >= 720:
        base = 0.8
    elif h >= 480:
        base = 0.5
    else:
        base = 0.2
    fps = record.fps
    if fps is None:
        return base
    if fps >= 60:
        return min(1.0, base + 0.10)
    if fps >= 24:
        return base
    return max(0.0, base - 0.10)


def _score_text_density(record: VideoRecord) -> float:
    chars = len(record.title) + len(record.description)
    chars += sum(len(s) for s in record.recipe_steps)
    if chars <= 0:
        return 0.0
    return min(1.0, math.log1p(chars) / math.log1p(_TARGET_TEXT_CHARS))


def _score_has_steps(record: VideoRecord) -> float:
    return 1.0 if record.recipe_steps else 0.0


def _tokenise(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


def _score_procedural_density(record: VideoRecord) -> float:
    tokens = _tokenise(record.title)
    tokens += _tokenise(record.description)
    for step in record.recipe_steps:
        tokens += _tokenise(step)
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in PROCEDURAL_VERBS)
    density = hits / len(tokens)
    return min(1.0, density / 0.05)


def _score_language_known(record: VideoRecord) -> float:
    return 1.0 if record.language else _NEUTRAL_UNKNOWN


_COMPONENTS = {
    "license_tier": _score_license_tier,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_density": _score_procedural_density,
    "language_known": _score_language_known,
}


def score_record(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS.values())
    if total_weight <= 0:
        return 0.0
    raw = sum(WEIGHTS[name] * fn(record) for name, fn in _COMPONENTS.items())
    return raw / total_weight


def score_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record(r)) for r in records]


def component_breakdown(record: VideoRecord) -> dict[str, float]:
    """Debug helper: per-component scores for a record."""
    return {name: fn(record) for name, fn in _COMPONENTS.items()}
