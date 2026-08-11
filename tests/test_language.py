from datetime import UTC, datetime

from specint.quality import detect_language, language_confidence, language_hint
from specint.records import Provenance, VideoRecord


def _rec(title: str, description: str = "") -> VideoRecord:
    return VideoRecord(
        id="t:x",
        source="t",
        source_native_id="x",
        url="https://example.test/x",
        title=title,
        description=description,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


def test_detect_language_returns_none_for_empty():
    lang, conf = detect_language("")
    assert lang is None
    assert conf == 0.0


def test_detect_language_recognises_english_stop_words():
    lang, conf = detect_language("how to cook the perfect pasta with garlic and butter")
    assert lang == "en"
    assert 0.0 < conf <= 1.0


def test_detect_language_recognises_spanish():
    lang, conf = detect_language("cómo cocinar una tortilla de patatas con cebolla")
    assert lang == "es"
    assert conf > 0.0


def test_detect_language_recognises_cjk_and_kana():
    lang_ja, conf_ja = detect_language("料理レシピの作り方")
    assert lang_ja == "ja"
    assert conf_ja > 0.4

    lang_zh, _ = detect_language("烹饪食谱做菜方法")
    assert lang_zh == "zh"


def test_language_confidence_uses_title_and_description():
    r = _rec("Knife skills demo", description="Chop onions safely with the correct grip.")
    assert 0.0 < language_confidence(r) <= 1.0
    assert language_hint(r) in {"en", "es", "fr", "it", "de", "pt"}


def test_language_confidence_empty_text_is_zero():
    r = _rec("", description="")
    assert language_confidence(r) == 0.0
