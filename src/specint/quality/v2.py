"""Quality scorer v2 (additive, backwards-comparable to v1).

Motivation (from Adversarial-Agent plan 2026-07-14):

* v1 is dominated by `license_clean` (0.35) and `resolution` (0.20).
  A 1080p CC-BY record with an empty title scores ≥ 0.55 by default.
* `has_steps` is binary; a wikimedia video with rich procedural
  narration in its *description* gets zero credit.
* We never penalise records whose title+description is essentially
  empty. That is exactly the kind of noise a corpus builder should
  reject.

v2 keeps all v1 components with unchanged weights (so v2 ≥ v1 on
license-clean, resolution-rich, high-text records) and adds:

* `text_density_min` — a hard *cap* at 0.4 when title+description is
  under 40 characters. This runs after the weighted sum so a bare
  CC-BY 1080p record with an empty title lands at ≤ 0.4 instead of
  ≥ 0.55.
* `procedural_verb` (weight 0.10) — density of cooking-procedural
  verbs in title + description + recipe_steps. Not a keyword match:
  we count occurrences of a small English procedural-verb lexicon.
* `english_signal` (weight 0.05) — soft signal that the record's
  language is either declared English (BCP-47 starts with "en") or
  ASCII-dominant. Intentionally low weight (≤ 0.10 combined with
  procedural_verb English-verb bias) so we don't encode "English =
  quality" — non-English records that clear v1 stay comparable via
  the v1 scorer, which the registry still exposes.

v2's total weight sum is normalised so `mean_quality` remains in
[0, 1]. All components are pure and unit-tested.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from specint.quality.metrics import (
    _score_duration,
    _score_has_steps,
    _score_license,
    _score_resolution,
    _score_text_density,
)
from specint.records import VideoRecord

WEIGHTS: dict[str, float] = {
    "license_clean": 0.30,
    "duration": 0.15,
    "resolution": 0.20,
    "text_density": 0.10,
    "has_steps": 0.10,
    "procedural_verb": 0.10,
    "english_signal": 0.05,
}

TEXT_DENSITY_MIN_CHARS = 40
TEXT_DENSITY_MIN_CAP = 0.4

PROCEDURAL_VERBS: frozenset[str] = frozenset(
    {
        "chop",
        "dice",
        "mince",
        "slice",
        "grate",
        "peel",
        "boil",
        "simmer",
        "saute",
        "sauté",
        "fry",
        "roast",
        "bake",
        "grill",
        "sear",
        "braise",
        "stir",
        "whisk",
        "fold",
        "knead",
        "toss",
        "combine",
        "mix",
        "blend",
        "reduce",
        "deglaze",
        "temper",
        "poach",
        "steam",
        "marinate",
        "season",
        "toast",
        "caramelize",
        "caramelise",
        "melt",
        "cook",
        "cool",
        "rest",
        "add",
        "pour",
        "drain",
        "rinse",
        "wash",
        "measure",
        "cut",
        "heat",
        "preheat",
    }
)

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+")


def _combined_text(record: VideoRecord) -> str:
    parts = [record.title or "", record.description or ""]
    parts.extend(record.recipe_steps)
    return " ".join(parts)


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _score_procedural_verb(record: VideoRecord) -> float:
    tokens = _tokenise(_combined_text(record))
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in PROCEDURAL_VERBS)
    if hits <= 0:
        return 0.0
    density = hits / len(tokens)
    return min(1.0, density / 0.05)  # 5% verb density saturates


def _score_english_signal(record: VideoRecord) -> float:
    lang = (record.language or "").lower()
    if lang.startswith("en") or lang == "eng":
        return 1.0
    text = _combined_text(record)
    if not text:
        return 0.0
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    all_letters = sum(1 for c in text if c.isalpha())
    if all_letters == 0:
        return 0.0
    ratio = ascii_letters / all_letters
    if ratio >= 0.9:
        return 0.8
    if ratio >= 0.6:
        return 0.4
    return 0.0


_COMPONENTS = {
    "license_clean": _score_license,
    "duration": _score_duration,
    "resolution": _score_resolution,
    "text_density": _score_text_density,
    "has_steps": _score_has_steps,
    "procedural_verb": _score_procedural_verb,
    "english_signal": _score_english_signal,
}


def _apply_text_density_gate(record: VideoRecord, raw: float) -> float:
    chars = len(record.title or "") + len(record.description or "")
    if chars < TEXT_DENSITY_MIN_CHARS:
        return min(raw, TEXT_DENSITY_MIN_CAP)
    return raw


def score_record(record: VideoRecord) -> float:
    total_weight = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[name] * fn(record) for name, fn in _COMPONENTS.items())
    raw = raw / total_weight if total_weight else 0.0
    return _apply_text_density_gate(record, raw)


def score_records(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r.with_quality(score_record(r)) for r in records]
