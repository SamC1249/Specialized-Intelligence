"""Curated cooking search-term dictionary (multilingual).

Rationale: the seed adversarial plan calls out that English-only terms
under-yield in Commons/Archive/PeerTube. This module lets adapters
compose queries across languages without redefining strings locally.

Add a new language by extending `COOKING_TERMS`. Keep the top-3
highest-frequency, culturally-neutral cooking words per language to
avoid over-fitting to a single cuisine.

Also exports `expand_query`: given a `SourceQuery`, return one query per
supported language (still an OR of terms upstream).
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.records import SourceQuery

COOKING_TERMS: dict[str, tuple[str, ...]] = {
    "en": ("cooking", "recipe", "kitchen"),
    "es": ("cocina", "receta", "cocinar"),
    "fr": ("cuisine", "recette", "cuisiner"),
    "de": ("kochen", "rezept", "küche"),
    "it": ("cucina", "ricetta", "cucinare"),
    "pt": ("cozinha", "receita", "cozinhar"),
    "ja": ("料理", "レシピ", "作り方"),
}


def all_terms(langs: Iterable[str] | None = None) -> list[str]:
    langs = tuple(langs) if langs is not None else tuple(COOKING_TERMS.keys())
    seen: list[str] = []
    for lang in langs:
        for t in COOKING_TERMS.get(lang, ()):
            if t not in seen:
                seen.append(t)
    return seen


def expand_query(query: SourceQuery, langs: Iterable[str] | None = None) -> list[SourceQuery]:
    """Return one query per language. Preserves `max_results` and `language` hints."""
    langs = list(langs) if langs is not None else list(COOKING_TERMS.keys())
    out: list[SourceQuery] = []
    for lang in langs:
        terms = list(COOKING_TERMS.get(lang, ()))
        if not terms:
            continue
        out.append(SourceQuery(terms=terms, max_results=query.max_results, language=lang))
    return out
