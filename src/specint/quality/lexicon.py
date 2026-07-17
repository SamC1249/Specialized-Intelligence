"""Multi-lingual cooking lexicon (seed).

Each language contributes a small hand-picked set of *cooking nouns*
(dish/ingredient/technique) and *imperative cooking verbs*. Verbs are
stored in a language-agnostic pool because their morphology varies but
they all contribute to the "procedural density" signal.

We deliberately keep this list short and legally trivial (single words,
not curated corpora). Callers can extend it via
`add_language(lang, nouns, verbs)`.

Design goals:
  - Offline, deterministic, hashable.
  - Extensible: new language = one small dict.
  - No external NLP dependency (langdetect / spaCy / etc.). We use
    simple case-folded substring hits — good enough for a coarse
    signal that costs microseconds.

Reviewer note (from the 2026-07-17 plan): the multilingual seed here
is intentionally tiny. Grow it via community PRs, not autogeneration,
so language coverage stays auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguagePack:
    lang: str
    nouns: frozenset[str]
    verbs: frozenset[str]


_SEED_PACKS: tuple[LanguagePack, ...] = (
    LanguagePack(
        lang="en",
        nouns=frozenset(
            {
                "recipe",
                "cooking",
                "kitchen",
                "bake",
                "grill",
                "sauce",
                "dough",
                "knife",
                "pan",
                "onion",
                "garlic",
                "pasta",
                "bread",
                "soup",
                "stew",
                "dessert",
            }
        ),
        verbs=frozenset(
            {
                "chop",
                "dice",
                "mince",
                "slice",
                "saute",
                "simmer",
                "boil",
                "roast",
                "fry",
                "bake",
                "whisk",
                "stir",
                "fold",
                "sear",
                "grate",
                "peel",
                "season",
            }
        ),
    ),
    LanguagePack(
        lang="es",
        nouns=frozenset(
            {
                "receta",
                "cocina",
                "cocinar",
                "sopa",
                "salsa",
                "arroz",
                "pollo",
                "carne",
                "ajo",
                "cebolla",
                "pan",
                "postre",
                "sarten",
                "horno",
            }
        ),
        verbs=frozenset(
            {"picar", "sofreir", "hervir", "asar", "freir", "hornear", "batir", "mezclar", "pelar"}
        ),
    ),
    LanguagePack(
        lang="fr",
        nouns=frozenset(
            {
                "recette",
                "cuisine",
                "cuisiner",
                "sauce",
                "pate",
                "pain",
                "soupe",
                "poulet",
                "boeuf",
                "ail",
                "oignon",
                "four",
                "poele",
            }
        ),
        verbs=frozenset(
            {"hacher", "revenir", "mijoter", "bouillir", "rotir", "frire", "cuire", "melanger"}
        ),
    ),
    LanguagePack(
        lang="it",
        nouns=frozenset(
            {
                "ricetta",
                "cucina",
                "pasta",
                "sugo",
                "pane",
                "zuppa",
                "pollo",
                "carne",
                "aglio",
                "cipolla",
                "forno",
                "padella",
            }
        ),
        verbs=frozenset(
            {"tagliare", "soffriggere", "bollire", "arrostire", "friggere", "cuocere", "mescolare"}
        ),
    ),
    LanguagePack(
        lang="ja",
        nouns=frozenset(
            {"レシピ", "料理", "調理", "パン", "米", "肉", "鶏", "醤油", "味噌", "スープ", "麺"}
        ),
        verbs=frozenset({"炒める", "煮る", "焼く", "揚げる", "切る", "混ぜる"}),
    ),
    LanguagePack(
        lang="hi",
        nouns=frozenset(
            {
                "रेसिपी",
                "खाना",
                "पकाना",
                "मसाला",
                "प्याज",
                "लहसुन",
                "आटा",
                "रोटी",
                "चावल",
                "सब्ज़ी",
            }
        ),
        verbs=frozenset({"काटना", "भूनना", "पकाना", "उबालना", "मिलाना"}),
    ),
)


@dataclass
class Lexicon:
    packs: list[LanguagePack] = field(default_factory=lambda: list(_SEED_PACKS))

    def add_language(self, lang: str, nouns: set[str], verbs: set[str]) -> None:
        self.packs.append(
            LanguagePack(lang=lang, nouns=frozenset(nouns), verbs=frozenset(verbs)),
        )

    def match_language(self, text: str) -> str | None:
        """Return the language whose lexicon best matches `text`, or None.

        "Best" = highest total (nouns + verbs) hit count. Ties go to
        the pack registered first (English by default).
        """
        if not text:
            return None
        haystack = text.casefold()
        best_hits = 0
        best_lang: str | None = None
        for pack in self.packs:
            hits = 0
            for term in pack.nouns:
                if term in haystack:
                    hits += 1
            for verb in pack.verbs:
                if verb in haystack:
                    hits += 1
            if hits > best_hits:
                best_hits = hits
                best_lang = pack.lang
        return best_lang

    def noun_hits(self, text: str) -> int:
        if not text:
            return 0
        haystack = text.casefold()
        return sum(1 for pack in self.packs for term in pack.nouns if term in haystack)

    def verb_hits(self, text: str) -> int:
        if not text:
            return 0
        haystack = text.casefold()
        return sum(1 for pack in self.packs for verb in pack.verbs if verb in haystack)


DEFAULT_LEXICON = Lexicon()
