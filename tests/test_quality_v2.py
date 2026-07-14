"""Tests for the v2 scorer.

We assert three invariants (see docs/plan-2026-07-14.md):
  1. `score_record_v2` returns a value in [0, 1] on every fixture record.
  2. A CC-BY-SA English record with procedural narration scores strictly
     higher on v2 than a same-license non-English record with the same
     duration and resolution — proving language-signal and procedural
     components are actually firing.
  3. `score_record_v2` never *drops* a license-clean record below the
     redistributable license floor of ~0.32/(sum weights) ≈ 0.31.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.quality.v2 import (
    WEIGHTS_V2,
    _score_english_signal,
    _score_procedural,
    score_record_v2,
)
from specint.records import SourceQuery
from specint.sources.wikimedia import WikimediaCommonsSource


def _wm_records(fixtures_dir: Path, filename: str):
    raw = json.loads((fixtures_dir / "wikimedia" / filename).read_text())
    return WikimediaCommonsSource().parse(raw, SourceQuery(terms=["cooking"]))


def test_v2_in_unit_interval(fixtures_dir: Path):
    records = _wm_records(fixtures_dir, "search_pasta.json")
    for r in records:
        s = score_record_v2(r)
        assert 0.0 <= s <= 1.0


def test_v2_procedural_and_english_activate(fixtures_dir: Path):
    english = _wm_records(fixtures_dir, "search_pasta.json")[0]
    english = english.model_copy(
        update={
            "description": (
                "Boil water in a large pot. Then chop the garlic, sauté it in butter, "
                "stir in cream, whisk gently, and season with salt and pepper."
            ),
        }
    )
    non_english = english.model_copy(
        update={
            "language": "fr",
            "title": "Cuisson des pâtes",
            "description": (
                "Faire bouillir l'eau. Puis émincer l'ail. Faire revenir dans du beurre. "
                "Remuer avec la crème. Assaisonner."
            ),
        }
    )
    assert _score_procedural(english) > 0.2
    assert _score_english_signal(english) >= _score_english_signal(non_english)
    assert score_record_v2(english) > score_record_v2(non_english)


def test_v2_license_floor_for_redistributable(fixtures_dir: Path):
    for r in _wm_records(fixtures_dir, "search_pasta.json"):
        if r.license.is_redistributable:
            floor = WEIGHTS_V2["license_clean"] / sum(WEIGHTS_V2.values()) - 1e-9
            assert score_record_v2(r) >= floor


def test_procedural_zero_on_empty_corpus(fixtures_dir: Path):
    r = _wm_records(fixtures_dir, "search_pasta.json")[0]
    empty = r.model_copy(update={"title": "", "description": "", "recipe_steps": []})
    assert _score_procedural(empty) == 0.0
    assert _score_english_signal(empty) == 0.0
