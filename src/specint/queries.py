"""Multilingual cooking seed-term catalog.

English-only seed terms systematically ignore the non-anglophone cooking
web (H5 in `docs/plan-2026-09-15.md`). This module ships a hand-curated
seed set for the languages that together cover the bulk of the
license-permissive food video web:

    en, es, fr, de, it, pt, ja, zh

Each language gets a short, high-signal list (verb + object pairs are
preferred over single nouns because upstream search engines tokenize
them better). Use `build_multilingual_queries()` to expand these into
`SourceQuery` objects.

The catalog is deliberately small and hand-audited: this file is a
contract with downstream `compare` runs, and we want any translation
change to be a code review, not a data import.
"""

from __future__ import annotations

from specint.records import SourceQuery

MULTILINGUAL_COOKING_TERMS: dict[str, list[str]] = {
    "en": ["cooking recipe", "how to cook", "knife skills", "baking tutorial"],
    "es": ["receta de cocina", "cómo cocinar", "cocina paso a paso"],
    "fr": ["recette de cuisine", "cuisine pas à pas", "cours de cuisine"],
    "de": ["kochrezept", "kochen lernen", "backen anleitung"],
    "it": ["ricetta di cucina", "cucina passo passo", "cucinare in casa"],
    "pt": ["receita culinária", "como cozinhar", "aula de cozinha"],
    "ja": ["料理レシピ", "作り方", "調理"],
    "zh": ["烹饪教程", "菜谱", "做菜"],
}


def build_multilingual_queries(max_results: int = 25) -> list[SourceQuery]:
    """One `SourceQuery` per language, terms fixed to that language's seed list."""
    out: list[SourceQuery] = []
    for lang, terms in MULTILINGUAL_COOKING_TERMS.items():
        out.append(SourceQuery(terms=list(terms), max_results=max_results, language=lang))
    return out


def language_coverage() -> list[str]:
    return sorted(MULTILINGUAL_COOKING_TERMS.keys())
