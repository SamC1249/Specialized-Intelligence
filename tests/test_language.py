from specint.quality.language import SUPPORTED, confidence, detect, detect_many


def test_detect_returns_none_on_empty():
    assert detect("") is None
    assert detect("   ") is None
    assert confidence("") == 0.0


def test_detect_english_recipe_text():
    text = (
        "How to make a classic French onion soup step by step with caramelised "
        "onions thyme gruyere toast and a splash of dry white wine every step timed"
    )
    assert detect(text) == "en"


def test_detect_italian_recipe_text():
    text = (
        "In una pentola capiente far soffriggere la cipolla tritata con olio "
        "extravergine di oliva quindi unire il pomodoro e il basilico"
    )
    assert detect(text) == "it"


def test_detect_japanese_uses_script_hint():
    text = "玉ねぎとにんじんを細かく切り、フライパンに油を入れて中火で炒めます"
    assert detect(text) == "ja"


def test_confidence_scales_with_length():
    short = confidence("hi")
    longer = confidence(
        "This is a much longer English sentence about cooking pasta with "
        "tomato sauce onions and garlic that should raise the confidence a lot"
    )
    assert short < longer
    assert longer <= 1.0


def test_confidence_never_full_on_tiny_input():
    assert confidence("hi") < 1.0
    assert confidence("hola") < 1.0


def test_supported_covers_common_languages():
    for expected in ("en", "es", "fr", "de", "it", "pt", "ja", "zh", "ar", "ru"):
        assert expected in SUPPORTED


def test_detect_many_matches_detect():
    inputs = ["how to make pasta with tomato sauce and basil", "玉ねぎとにんじん"]
    outputs = detect_many(inputs)
    assert outputs[0] == detect(inputs[0])
    assert outputs[1] == "ja"
