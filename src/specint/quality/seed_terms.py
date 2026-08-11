"""Curated multilingual cooking / recipe search seeds.

Each entry maps an ISO 639-1 language code to a short list of high-signal
seed terms. Kept intentionally small so the union stays under the
per-source query budget; upstream APIs are query-count-limited, not
term-count-limited.

Adding a language:
  1. Append a language code + 3-6 seed terms in the target language.
  2. Add at least one fixture record with a title in that language so the
     `quality.language` detector's coverage is proven in CI.
  3. Update `all_seed_terms` callers if they hard-code the language set.
"""

from __future__ import annotations

from collections.abc import Iterable

SEED_TERMS: dict[str, list[str]] = {
    "en": ["cooking", "recipe", "how to cook", "knife skills", "baking"],
    "es": ["cocina", "receta", "cómo cocinar", "repostería"],
    "fr": ["cuisine", "recette", "pâtisserie", "cuisiner"],
    "it": ["cucina", "ricetta", "pasta fatta in casa"],
    "de": ["kochen", "rezept", "backen"],
    "pt": ["cozinha", "receita", "como cozinhar"],
    "ja": ["料理", "レシピ", "作り方"],
    "zh": ["烹饪", "食谱", "做菜"],
    "ko": ["요리", "레시피"],
    "hi": ["खाना बनाना", "रेसिपी"],
    "ar": ["طبخ", "وصفة"],
}

SUPPORTED_LANGS: tuple[str, ...] = tuple(SEED_TERMS.keys())


def seed_terms_for(lang: str) -> list[str]:
    return list(SEED_TERMS.get(lang.lower(), []))


def all_seed_terms(langs: Iterable[str] | None = None) -> list[str]:
    """Return de-duplicated union of seed terms across `langs`.

    Ordering: preserves the declaration order in `SEED_TERMS` so callers
    get deterministic queries (matters for reproducible benchmarks).
    """
    if langs is None:
        selected = SUPPORTED_LANGS
    else:
        selected = tuple(dict.fromkeys(lang.lower() for lang in langs))
    seen: set[str] = set()
    out: list[str] = []
    for lang in selected:
        for term in SEED_TERMS.get(lang, []):
            if term not in seen:
                seen.add(term)
                out.append(term)
    return out
