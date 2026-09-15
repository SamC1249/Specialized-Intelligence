from specint.queries import (
    MULTILINGUAL_COOKING_TERMS,
    build_multilingual_queries,
    language_coverage,
)


def test_catalog_covers_expected_languages():
    assert set(MULTILINGUAL_COOKING_TERMS).issuperset({"en", "es", "fr", "de", "it", "ja", "zh"})


def test_every_language_has_nonempty_terms():
    for lang, terms in MULTILINGUAL_COOKING_TERMS.items():
        assert terms, f"language {lang} has no seed terms"
        assert all(isinstance(t, str) and t.strip() for t in terms)


def test_build_multilingual_queries_shape():
    qs = build_multilingual_queries(max_results=17)
    assert len(qs) == len(MULTILINGUAL_COOKING_TERMS)
    langs = {q.language for q in qs}
    assert langs == set(MULTILINGUAL_COOKING_TERMS.keys())
    for q in qs:
        assert q.max_results == 17
        assert q.terms == MULTILINGUAL_COOKING_TERMS[q.language]


def test_language_coverage_sorted():
    covers = language_coverage()
    assert covers == sorted(covers)
