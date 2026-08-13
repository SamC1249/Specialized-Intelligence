from specint.quality.language import (
    detect_language,
    matches_target,
    summarise,
)


def test_detect_language_english_from_stopwords():
    lang, conf = detect_language("How to cook a classic Italian pasta with garlic and butter")
    assert lang == "en"
    assert conf > 0.4


def test_detect_language_japanese_from_kana():
    lang, conf = detect_language("料理の基本 だしの作り方")
    assert lang == "ja"
    assert conf > 0.8


def test_detect_language_spanish_from_stopwords():
    lang, conf = detect_language("Cómo cocinar una paella valenciana con arroz y pollo")
    assert lang == "es"
    assert conf > 0.4


def test_detect_language_empty_and_symbols():
    assert detect_language("") == (None, 0.0)
    assert detect_language("   ") == (None, 0.0)
    assert detect_language(None) == (None, 0.0)
    assert detect_language("!!! 123 ???") == (None, 0.0)


def test_detect_language_short_input_caps_confidence():
    _, conf = detect_language("the cook")
    assert conf <= 0.5


def test_matches_target_none_returns_one():
    assert matches_target("Some cooking video", None) == 1.0


def test_matches_target_wrong_language_penalises():
    match = matches_target("料理の基本 だし", "en")
    assert match < 0.5


def test_matches_target_right_language_high():
    match = matches_target("How to cook a classic Italian pasta with the recipe", "en")
    assert match > 0.5


def test_summarise_aggregates_per_language():
    out = summarise(
        [
            "How to cook a classic Italian pasta with garlic",
            "Cómo cocinar una paella valenciana",
            "料理の基本 だし",
        ]
    )
    assert set(out.keys()) >= {"en", "es", "ja"}
    for conf in out.values():
        assert 0.0 <= conf <= 1.0
