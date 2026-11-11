"""Unit tests for `specint.quality.i18n`."""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.i18n import LEXICON, cooking_relevance, detect_language, languages_covered
from specint.records import License, Provenance, VideoRecord


def _rec(**kw):
    defaults = dict(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/1",
        title="",
        description="",
        language=None,
        duration_s=None,
        width=None,
        height=None,
        fps=None,
        license=License.UNKNOWN,
        provenance=Provenance(extractor="test", fetched_at=datetime(2026, 1, 1, tzinfo=UTC)),
    )
    defaults.update(kw)
    return VideoRecord(**defaults)


def test_languages_covered_include_core_set():
    assert set(languages_covered()) >= {"en", "es", "fr", "de", "it", "ja"}


def test_english_record_detected_and_scored():
    r = _rec(title="How to cook pasta", description="A quick recipe for a weeknight meal.")
    assert detect_language(r) == "en"
    score = cooking_relevance(r)
    assert 0.5 <= score <= 1.0


def test_spanish_record_detected_via_lexicon():
    r = _rec(title="Receta de paella", description="Cocina tradicional valenciana.")
    assert detect_language(r) == "es"
    assert cooking_relevance(r) >= 0.5


def test_japanese_record_detected_via_lexicon():
    r = _rec(title="伝統的な寿司の料理レシピ", description="寿司の調理手順")
    assert detect_language(r) == "ja"
    assert cooking_relevance(r) >= 0.5


def test_declared_language_wins_over_heuristic():
    r = _rec(title="Nature documentary", language="fr-CA")
    assert detect_language(r) == "fr"


def test_zero_signal_returns_zero():
    r = _rec(title="xyz", description="")
    assert cooking_relevance(r) == 0.0


def test_accent_folded_terms_match():
    r = _rec(title="Sauté technique")
    assert cooking_relevance(r) >= 0.5


def test_lexicon_is_lowercased_and_non_empty():
    for lang, words in LEXICON.items():
        assert words, f"{lang} lexicon is empty"
        for w in words:
            if lang != "ja":
                assert w == w.lower()
