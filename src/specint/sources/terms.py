"""Multilingual seed-term expansion for the cooking-video domain.

Adapters that only accept a single query string can just use
``expand_terms(query)`` to get a language-aware bag of terms. Adapters
that talk to APIs supporting a language filter should also pass
``query.effective_languages`` through.

Keeping the mapping in one file means the Adversarial-Agent can
inspect exactly what "cooking" means in each language without diffing
every adapter.
"""

from __future__ import annotations

from specint.records import SourceQuery

COOKING_TERMS: dict[str, tuple[str, ...]] = {
    "en": ("cooking", "recipe", "kitchen"),
    "es": ("cocina", "receta"),
    "fr": ("cuisine", "recette"),
    "de": ("kochen", "rezept"),
    "it": ("cucina", "ricetta"),
    "pt": ("cozinha", "receita"),
    "ja": ("料理", "レシピ"),
    "zh": ("烹饪", "食谱"),
    "ko": ("요리", "레시피"),
    "ar": ("طبخ", "وصفة"),
    "hi": ("खाना पकाना", "रेसिपी"),
    "ru": ("готовка", "рецепт"),
}


def expand_terms(query: SourceQuery) -> list[str]:
    """Return the effective set of terms for `query`.

    Rules:
      * If the caller specified explicit terms, keep them as-is (do not
        translate — the caller knows best).
      * Merge in the per-language seed terms for every effective
        language of the query.
      * De-duplicate while preserving insertion order.
    """
    out: list[str] = []
    seen: set[str] = set()
    for t in query.terms:
        if t not in seen:
            out.append(t)
            seen.add(t)
    for lang in query.effective_languages:
        for term in COOKING_TERMS.get(lang, ()):
            if term not in seen:
                out.append(term)
                seen.add(term)
    return out


def known_languages() -> list[str]:
    return sorted(COOKING_TERMS)
