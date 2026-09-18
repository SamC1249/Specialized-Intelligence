from specint.quality.language import detect_language


def test_detect_english():
    text = "The chef is cooking a pasta with butter and garlic for the family"
    assert detect_language(text) == "en"


def test_detect_spanish():
    text = "La receta de la cocina española con aceite de oliva y ajo para la familia"
    assert detect_language(text) == "es"


def test_detect_french():
    text = "La cuisine française pour les enfants avec de la crème et du beurre"
    assert detect_language(text) == "fr"


def test_detect_german():
    text = "Der Koch bereitet ein Rezept für die Familie mit Butter und Knoblauch"
    assert detect_language(text) == "de"


def test_detect_none_when_no_evidence():
    assert detect_language("") is None
    assert detect_language("xyz qqq") is None
    assert detect_language(None, None) is None


def test_detect_tie_returns_none():
    assert detect_language("plap qwrt zzyx aaaa bbbb") is None
