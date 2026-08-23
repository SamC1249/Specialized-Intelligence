"""Multilingual cooking seed terms.

Curated, hand-audited seed vocabulary for driving search queries against
the source registry. Coverage is deliberately broad but shallow — enough
to surface each language's dominant "how to cook X" query term without
turning this file into an ontology.

Adding a language:
  1. Add a BCP-47 key to ``SEEDS_BY_LANG``.
  2. Keep terms lowercase; the adapters uppercase / URL-encode as needed.
  3. Prefer generic cooking / recipe / technique roots over specific
     dish names. A follow-up module can add cuisine-specific expansions.
"""

from __future__ import annotations

from collections.abc import Iterable

SEEDS_BY_LANG: dict[str, tuple[str, ...]] = {
    "en": ("cooking", "recipe", "how to cook", "kitchen tutorial"),
    "es": ("cocina", "receta", "cómo cocinar", "tutorial de cocina"),
    "fr": ("cuisine", "recette", "comment cuisiner", "tutoriel cuisine"),
    "it": ("cucina", "ricetta", "come cucinare"),
    "de": ("kochen", "rezept", "kochanleitung"),
    "pt": ("cozinha", "receita", "como cozinhar"),
    "ja": ("料理", "レシピ", "作り方"),
    "zh": ("烹饪", "食谱", "做菜", "菜谱"),
    "ko": ("요리", "레시피", "만드는 법"),
    "hi": ("पकाना", "रेसिपी", "खाना बनाना"),
    "ar": ("طبخ", "وصفة", "طريقة الطبخ"),
    "ru": ("готовить", "рецепт", "как приготовить"),
}


def seeds_for(langs: Iterable[str] | None = None) -> list[str]:
    """Return the flat, deduplicated list of seed terms for ``langs``.

    ``langs=None`` returns every seed in insertion order. Unknown language
    codes are silently skipped — callers should validate their inputs.
    """
    keys = list(SEEDS_BY_LANG.keys()) if langs is None else list(langs)
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        for term in SEEDS_BY_LANG.get(k, ()):
            if term not in seen:
                seen.add(term)
                out.append(term)
    return out


def known_languages() -> list[str]:
    return list(SEEDS_BY_LANG.keys())
