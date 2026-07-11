from specint.records import SourceQuery
from specint.sources.terms import COOKING_TERMS, expand_terms, known_languages


def test_expand_terms_english_default_keeps_input():
    q = SourceQuery(terms=["knife skills"])
    assert expand_terms(q) == ["knife skills"]


def test_expand_terms_languages_add_seed_terms():
    q = SourceQuery(terms=["cooking"], languages=["fr", "es"])
    out = expand_terms(q)
    assert "cooking" in out
    for w in COOKING_TERMS["fr"] + COOKING_TERMS["es"]:
        assert w in out


def test_expand_terms_preserves_order_and_dedupes():
    q = SourceQuery(terms=["cocina"], languages=["es", "es"])
    out = expand_terms(q)
    assert out[0] == "cocina"
    assert out.count("cocina") == 1
    assert out.count("receta") == 1


def test_source_query_language_backcompat_still_works():
    q = SourceQuery(terms=["cooking"], language="ja")
    assert q.effective_languages == ["ja"]
    out = expand_terms(q)
    assert "料理" in out


def test_known_languages_stable_and_nonempty():
    langs = known_languages()
    assert langs and len(langs) == len(set(langs))
    assert "en" in langs and "ja" in langs
