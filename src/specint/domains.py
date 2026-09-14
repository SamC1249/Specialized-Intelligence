"""Domain profiles: multilingual seed-term registries.

The cooking-specific narrow goal is one instance. Every collector in
`specint` must accept a `SourceQuery` — i.e. free-text terms — and this
module keeps the *canonical seed vocabulary per (domain, language)* so
we can rerun the harness across domains without editing the CLI or the
adapters.

Adding a new domain:
  1. Add an entry to `DOMAINS` with one language block per BCP-47 code.
  2. Keep the tuple short (~5 terms) — this is a seed, not a curriculum.
  3. Add or extend a test in `tests/test_domains.py`.

Adding a new language to an existing domain:
  * Add a `<lang>: (...,)` entry to that domain's block.
  * If the term contains non-ASCII characters, please add it in the
    source file's canonical Unicode form (no HTML entities).

`terms_for(domain, language=None)` returns the union across all
languages when `language is None`, else the single language block.
"""

from __future__ import annotations

DOMAINS: dict[str, dict[str, tuple[str, ...]]] = {
    "cooking": {
        "en": ("cooking", "recipe", "kitchen", "baking", "how to cook"),
        "es": ("cocina", "receta", "cocinar", "hornear"),
        "fr": ("cuisine", "recette", "cuisiner", "pâtisserie"),
        "de": ("kochen", "rezept", "küche", "backen"),
        "it": ("cucina", "ricetta", "cucinare", "pasticceria"),
        "pt": ("cozinha", "receita", "cozinhar"),
        "ja": ("料理", "レシピ", "作り方"),
        "zh": ("烹饪", "食谱", "做法"),
        "ru": ("готовка", "рецепт", "кухня"),
    },
    "surgery": {
        "en": (
            "surgical procedure",
            "laparoscopic",
            "endoscopic",
            "operating room",
            "medical training",
        ),
        "es": ("procedimiento quirúrgico", "cirugía", "endoscopia"),
        "fr": ("procédure chirurgicale", "chirurgie", "endoscopie"),
        "de": ("chirurgischer eingriff", "chirurgie", "endoskopie"),
    },
    "manufacturing": {
        "en": (
            "manufacturing process",
            "assembly line",
            "machining",
            "welding tutorial",
            "3d printing",
        ),
        "de": ("fertigung", "montage", "werkstatt"),
        "ja": ("製造", "組み立て"),
        "zh": ("制造", "装配"),
    },
    "sports_drills": {
        "en": (
            "training drill",
            "coaching drill",
            "technique breakdown",
            "footwork",
            "form check",
        ),
        "es": ("entrenamiento", "ejercicio deportivo"),
        "fr": ("entraînement", "exercice sportif"),
    },
    "lab_protocol": {
        "en": (
            "lab protocol",
            "laboratory procedure",
            "wet lab",
            "pipetting",
            "titration",
        ),
        "de": ("laborprotokoll", "laborversuch"),
    },
}


def list_domains() -> list[str]:
    return sorted(DOMAINS.keys())


def list_languages(domain: str) -> list[str]:
    if domain not in DOMAINS:
        raise KeyError(f"unknown domain: {domain}")
    return sorted(DOMAINS[domain].keys())


def terms_for(domain: str, language: str | None = None) -> list[str]:
    """Return seed terms for `(domain, language)`.

    If `language` is None, returns the union across every language in
    that domain (deduplicated, order-stable).
    """
    if domain not in DOMAINS:
        raise KeyError(f"unknown domain: {domain}")
    if language is None:
        seen: dict[str, None] = {}
        for terms in DOMAINS[domain].values():
            for t in terms:
                seen.setdefault(t, None)
        return list(seen.keys())
    if language not in DOMAINS[domain]:
        raise KeyError(f"domain {domain!r} has no language {language!r}")
    return list(DOMAINS[domain][language])
