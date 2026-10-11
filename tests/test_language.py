from specint.quality.language import SEED_TERMS, detect_language, seed_terms


def test_empty_returns_none():
    assert detect_language("") is None
    assert detect_language(None) is None
    assert detect_language("   ") is None


def test_cjk_scripts_are_classified():
    assert detect_language("簡単な料理のレシピ") == "ja"  # hiragana + han
    assert detect_language("レシピ") == "ja"
    assert detect_language("요리 레시피") == "ko"
    assert detect_language("家常菜食谱") == "zh"
    assert detect_language("Как готовить борщ") == "ru"
    assert detect_language("طريقة الطبخ") == "ar"
    assert detect_language("खाना बनाना") == "hi"
    assert detect_language("מתכון בישול") == "he"


def test_latin_stopword_vote():
    assert detect_language("Recipe for the perfect omelette") == "en"
    assert detect_language("Receta de tortilla con patatas") == "es"
    assert detect_language("Recette de omelette avec pommes de terre") == "fr"
    assert detect_language("Rezept für Rührei mit Kartoffeln") == "de"


def test_latin_fallback_to_english_when_ambiguous():
    assert detect_language("Nasi Goreng") == "en"


def test_seed_terms_has_fallback_and_covers_all_keys():
    assert seed_terms(None) == SEED_TERMS["en"]
    assert seed_terms("xx") == SEED_TERMS["en"]
    assert seed_terms("en-US") == SEED_TERMS["en"]
    for tag in SEED_TERMS:
        assert len(seed_terms(tag)) >= 2
