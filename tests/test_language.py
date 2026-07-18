from specint.quality.language import annotate_language, detect_language


def test_detect_english_from_stopwords():
    assert detect_language("The best cooking recipe for pancakes with butter") == "en"


def test_detect_spanish_from_stopwords():
    assert detect_language("La mejor receta para la cocina con mantequilla") == "es"


def test_detect_french_from_stopwords():
    assert detect_language("La recette de cuisine avec la vidéo et le beurre") == "fr"


def test_detect_japanese_by_script():
    assert detect_language("ラーメンの作り方 (how to make ramen)") == "ja"


def test_detect_russian_by_script():
    assert detect_language("Рецепт борща и говядиной и капустой") == "ru"


def test_returns_none_when_ambiguous():
    assert detect_language("abc def") is None


def test_returns_none_on_empty():
    assert detect_language("") is None
    assert detect_language("   ") is None


def test_annotate_language_does_not_overwrite_existing():
    assert annotate_language("hello world", "", "en") == "en"
    assert annotate_language("hello world", "", "de") == "de"


def test_annotate_language_fills_missing():
    assert annotate_language("The recipe for cooking pasta", "with butter and cheese", None) == "en"


def test_annotate_language_returns_none_when_undetermined():
    assert annotate_language("", "", None) is None
