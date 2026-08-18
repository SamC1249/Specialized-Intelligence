"""Metadata-only quality scoring.

Each component returns a value in [0, 1]; the final score is a weighted
sum, also in [0, 1]. Scoring is deliberately *metadata-only* so we can
rank a backlog of millions of candidates before deciding which to
actually download.

Components:
  - license_clean       : 1 iff license is redistributable, else 0.
  - duration            : peaks at 5 minutes; decays out to ~1 hour.
  - resolution          : ramps by height buckets.
  - text_density        : total chars across title+description+steps.
  - has_steps           : 1 iff `recipe_steps` non-empty.
  - language_confidence : 1 iff BCP-47 hint set OR title/description
                          hits >= 2 stopwords of a supported language.
  - procedural_density  : verb-hit ratio over recipe steps + description.
  - recency             : linear decay from `published_at`; unknown → 0.5.
  - aspect_ratio_ok     : 1 iff aspect within a landscape sweet-spot.

Weight profiles:
  - default    : the historical (2026-06-20) mix, kept for regression.
  - procedural : rewards recipe-step-bearing sources (Common Crawl).
  - resolution : rewards high-res + long-duration (Commons, PeerTube).

Adding a component:
  1. Implement a new `_score_*` function returning a float in [0, 1].
  2. Add it to `_COMPONENTS`.
  3. Add a weight to every profile in `WEIGHT_PROFILES` (may be 0).
  4. Extend tests in `tests/test_quality.py` /
     `tests/test_quality_profiles.py` with the new bounds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime

from specint.records import VideoRecord

# ---------------------------------------------------------------------------
# Component functions
# ---------------------------------------------------------------------------


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


# --- language heuristic -----------------------------------------------------

_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "the",
            "and",
            "with",
            "for",
            "you",
            "your",
            "how",
            "to",
            "of",
            "a",
            "in",
            "on",
            "is",
            "it",
            "this",
            "that",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "de",
            "des",
            "du",
            "et",
            "avec",
            "pour",
            "une",
            "un",
            "à",
            "au",
            "aux",
            "dans",
            "est",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "y",
            "con",
            "para",
            "un",
            "una",
            "en",
            "es",
            "que",
            "por",
            "como",
        }
    ),
}

_WORD_RE = re.compile(r"[a-zàâçéèêëîïôûùüÿñæœáíóúñü]+", re.IGNORECASE)


def detect_language(text: str) -> str | None:
    """Deterministic stopword-based language detector.

    Returns the language code with the highest stopword hit count if that
    count is >= 2, else `None`. Ties break alphabetically so results are
    stable.
    """
    if not text:
        return None
    tokens = {t.lower() for t in _WORD_RE.findall(text)}
    if not tokens:
        return None
    best_lang: str | None = None
    best_hits = 0
    for lang, stops in sorted(_STOPWORDS.items()):
        hits = len(tokens & stops)
        if hits > best_hits:
            best_lang = lang
            best_hits = hits
    return best_lang if best_hits >= 2 else None


def _score_language_confidence(record: VideoRecord) -> float:
    if record.language:
        return 1.0
    text = " ".join([record.title, record.description])
    return 1.0 if detect_language(text) is not None else 0.0


# --- procedural density ----------------------------------------------------

_PROCEDURAL_VERBS: frozenset[str] = frozenset(
    {
        "add",
        "bake",
        "beat",
        "blend",
        "boil",
        "braise",
        "broil",
        "brown",
        "chill",
        "chop",
        "combine",
        "cook",
        "cool",
        "cover",
        "cut",
        "deglaze",
        "dice",
        "drain",
        "flip",
        "fold",
        "fry",
        "garnish",
        "glaze",
        "grate",
        "grill",
        "heat",
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
        "season",
        "serve",
        "sift",
        "simmer",
        "slice",
        "sprinkle",
        "steam",
        "stir",
        "toast",
        "toss",
        "whisk",
    }
)


def _score_procedural_density(record: VideoRecord) -> float:
    corpus = " ".join([record.description, *record.recipe_steps])
    if not corpus:
        return 0.0
    tokens = [t.lower() for t in _WORD_RE.findall(corpus)]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in _PROCEDURAL_VERBS)
    # A dense procedural transcript hits ~10% verbs; saturate at 10.
    return min(1.0, hits / 10.0)


# --- recency ---------------------------------------------------------------

_RECENCY_HORIZON_YEARS = 15.0


def _score_recency(record: VideoRecord) -> float:
    published = record.published_at
    if published is None:
        return 0.5  # unknown: neither reward nor penalize
    now = datetime.now(UTC)
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    age_years = max(0.0, (now - published).total_seconds() / (365.25 * 86400.0))
    if age_years >= _RECENCY_HORIZON_YEARS:
        return 0.0
    return 1.0 - age_years / _RECENCY_HORIZON_YEARS


# --- aspect ratio ----------------------------------------------------------


def _score_aspect_ratio_ok(record: VideoRecord) -> float:
    w, h = record.width, record.height
    if not w or not h or w <= 0 or h <= 0:
        return 0.5  # unknown → neutral
    aspect = w / h
    return 1.0 if 1.3 <= aspect <= 2.4 else 0.5


# ---------------------------------------------------------------------------
# Registry + profiles
# ---------------------------------------------------------------------------

_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "language_confidence": _score_language_confidence,
    "procedural_density": _score_procedural_density,
    "recency": _score_recency,
    "aspect_ratio_ok": _score_aspect_ratio_ok,
}


WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "default": {
        # Original 2026-06-20 mix kept for regression comparability.
        "license_clean": 0.35,
        "duration": 0.15,
        "resolution": 0.20,
        "text_density": 0.15,
        "has_steps": 0.15,
        # New signals contribute at zero weight in `default` so the
        # historical baseline JSON stays comparable byte-for-byte.
        "language_confidence": 0.0,
        "procedural_density": 0.0,
        "recency": 0.0,
        "aspect_ratio_ok": 0.0,
    },
    "procedural": {
        # Rewards sources that carry recipe steps / dense verb usage.
        "license_clean": 0.30,
        "duration": 0.05,
        "resolution": 0.05,
        "text_density": 0.15,
        "has_steps": 0.20,
        "language_confidence": 0.05,
        "procedural_density": 0.15,
        "recency": 0.0,
        "aspect_ratio_ok": 0.05,
    },
    "resolution": {
        # Rewards high-res, longer, landscape footage suitable for a
        # frame-tokenised world model.
        "license_clean": 0.30,
        "duration": 0.20,
        "resolution": 0.25,
        "text_density": 0.05,
        "has_steps": 0.05,
        "language_confidence": 0.05,
        "procedural_density": 0.0,
        "recency": 0.05,
        "aspect_ratio_ok": 0.05,
    },
}

# Backward-compatible alias used by older callers.
WEIGHTS: dict[str, float] = WEIGHT_PROFILES["default"]


def available_profiles() -> list[str]:
    return sorted(WEIGHT_PROFILES.keys())


def score_record(record: VideoRecord, profile: str = "default") -> float:
    weights = WEIGHT_PROFILES.get(profile)
    if weights is None:
        raise KeyError(f"unknown quality profile: {profile!r}")
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
    records: Iterable[VideoRecord],
    profile: str = "default",
) -> list[VideoRecord]:
    return [r.with_quality(score_record(r, profile=profile)) for r in records]
