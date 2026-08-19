from __future__ import annotations

from specint.records import SourceQuery
from specint.search_terms import COOKING_TERMS, all_terms, expand_query


def test_cooking_terms_have_all_supported_langs():
    for lang in ("en", "es", "fr", "de", "it", "pt", "ja"):
        assert lang in COOKING_TERMS
        assert len(COOKING_TERMS[lang]) >= 2


def test_all_terms_deduplicates_across_langs():
    terms = all_terms(["en", "en", "en"])
    assert len(terms) == len(set(terms))


def test_expand_query_produces_query_per_lang():
    base = SourceQuery(terms=["cooking"], max_results=10)
    expanded = expand_query(base, ["en", "es", "fr"])
    langs = {q.language for q in expanded}
    assert langs == {"en", "es", "fr"}
    for q in expanded:
        assert q.max_results == 10
