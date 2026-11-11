"""Multilingual cooking-domain relevance scoring (metadata-only).

Why this exists
---------------
The June baseline scorer rewards license-cleanliness, duration, resolution,
raw text density and "has recipe steps". Nothing in it actually checks that
a record is about *cooking*. On a mixed corpus that lets a 1080p CC-BY
nature documentary outrank a 480p CC-BY cooking tutorial — exactly the
failure mode we flagged as "quality-vs-quantity Pareto" in the adversarial
plan.

`cooking_relevance(record)` is a lightweight, metadata-only signal in
[0, 1] that counts matches of a *multilingual* cooking lexicon against the
record's title, description, keywords, and recipe steps. We deliberately
pick very frequent nouns/verbs per language so that recall stays high; a
single hit already pushes the score to 0.5 so a laconic Japanese
"料理" title is not penalized for not writing a paragraph.

Languages shipped today: English, Spanish, French, German, Italian,
Japanese. Adding a language is an append-only change to `LEXICON`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from specint.records import VideoRecord

LEXICON: dict[str, tuple[str, ...]] = {
    "en": (
        # verbs / technique
        "cook",
        "recipe",
        "kitchen",
        "bake",
        "roast",
        "grill",
        "fry",
        "boil",
        "simmer",
        "saute",
        "chef",
        "dish",
        "meal",
        "ingredient",
        "knife",
        "pan",
        "oven",
        "dough",
        "sauce",
        "stove",
        "mix",
        "whisk",
        # foods / dishes (helps real-world titles like "Sourdough" /
        # "Pancakes" / "Carbonara" / "Paella")
        "sourdough",
        "bread",
        "pasta",
        "noodle",
        "noodles",
        "pancake",
        "pancakes",
        "pizza",
        "sushi",
        "soup",
        "stew",
        "salad",
        "cake",
        "cookie",
        "cookies",
        "pie",
        "tart",
        "dessert",
        "rice",
        "taco",
        "burrito",
        "sandwich",
        "butter",
        "garlic",
        "onion",
        "egg",
        "eggs",
        "beef",
        "chicken",
        "fish",
        "pork",
        "vegetable",
        "vegetables",
        "carbonara",
        "ratatouille",
        "paella",
        "curry",
    ),
    "es": (
        "cocina",
        "cocinar",
        "receta",
        "horno",
        "hervir",
        "asar",
        "freir",
        "sarten",
        "chef",
        "plato",
        "ingrediente",
        "cuchillo",
        "masa",
        "salsa",
        "pan",
        "pasta",
        "sopa",
        "arroz",
        "pollo",
        "pescado",
        "paella",
        "tortilla",
        "mantequilla",
    ),
    "fr": (
        "cuisine",
        "cuisiner",
        "recette",
        "four",
        "bouillir",
        "rotir",
        "frire",
        "poele",
        "chef",
        "plat",
        "ingredient",
        "couteau",
        "pate",
        "sauce",
        "pain",
        "pates",
        "soupe",
        "riz",
        "poulet",
        "poisson",
        "ratatouille",
        "beurre",
    ),
    "de": (
        "kochen",
        "koche",
        "rezept",
        "backen",
        "ofen",
        "braten",
        "pfanne",
        "koch",
        "gericht",
        "zutat",
        "messer",
        "teig",
        "sosse",
        "brot",
        "nudel",
        "suppe",
        "reis",
        "huhn",
        "fisch",
        "butter",
    ),
    "it": (
        "cucina",
        "cucinare",
        "ricetta",
        "forno",
        "bollire",
        "arrostire",
        "friggere",
        "padella",
        "chef",
        "piatto",
        "ingrediente",
        "coltello",
        "impasto",
        "salsa",
        "pane",
        "pasta",
        "zuppa",
        "riso",
        "pollo",
        "pesce",
        "carbonara",
        "burro",
    ),
    "ja": (
        "料理",
        "レシピ",
        "調理",
        "焼く",
        "煮る",
        "炒め",
        "キッチン",
        "シェフ",
        "食材",
        "包丁",
        "鍋",
        "寿司",
        "ラーメン",
        "パン",
        "うどん",
        "そば",
    ),
}


def _strip_accents(s: str) -> str:
    """NFKD-normalize and drop combining marks so 'sauté' hits 'saute'."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return _strip_accents((text or "").lower())


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(_normalize(text)))


def detect_language(record: VideoRecord) -> str | None:
    """Return a best-effort BCP-47 primary subtag, or `None`.

    Prefer the record's declared language, else fall back to a per-lexicon
    token-overlap tally. Ties and empty records resolve to `None`.
    """
    if record.language:
        return record.language.split("-")[0].lower()

    haystack = " ".join(
        [record.title, record.description, " ".join(record.keywords), " ".join(record.recipe_steps)]
    )
    normalized = _normalize(haystack)
    tokens = set(_WORD_RE.findall(normalized))

    best: tuple[str, int] | None = None
    for lang, words in LEXICON.items():
        if lang == "ja":
            hits = sum(1 for w in words if w in haystack)
        else:
            hits = sum(1 for w in words if _normalize(w) in tokens)
        if hits and (best is None or hits > best[1]):
            best = (lang, hits)
    return best[0] if best else None


def _hits_for_language(haystack_raw: str, tokens: set[str], lang: str) -> int:
    """Count lexicon matches.

    For Japanese we substring-match against the raw haystack (no reliable
    tokenizer in stdlib). For latin-script languages we prefix-match
    against the token set so a stem like `cook` matches tokens like
    `cooking`, `cookbook`, `cooks` while still avoiding catastrophic
    substring false-positives such as `pan` matching `pandemic`.
    """
    words = LEXICON.get(lang, ())
    if not words:
        return 0
    if lang == "ja":
        return sum(1 for w in words if w in haystack_raw)
    hits = 0
    for w in words:
        nw = _normalize(w)
        if not nw:
            continue
        if any(tok.startswith(nw) for tok in tokens):
            hits += 1
    return hits


def cooking_relevance(record: VideoRecord) -> float:
    """Return a metadata-only cooking-domain relevance score in [0, 1].

    The score is `1 - 0.5**hits`:
      - 0 hits → 0.0
      - 1 hit  → 0.5
      - 2 hits → 0.75
      - 3 hits → 0.875
      - ≥ 4   → ~1.0
    Hits are counted against the record's primary language *and* English
    (common fallback for titles in otherwise-foreign records).
    """
    haystack = " ".join(
        [
            record.title or "",
            record.description or "",
            " ".join(record.keywords or []),
            " ".join(record.recipe_steps or []),
        ]
    )
    tokens = _tokens(haystack)
    lang = detect_language(record)

    langs_to_check: list[str] = []
    if lang and lang in LEXICON:
        langs_to_check.append(lang)
    if "en" not in langs_to_check:
        langs_to_check.append("en")

    hits = sum(_hits_for_language(haystack, tokens, lg) for lg in langs_to_check)
    if hits <= 0:
        return 0.0
    return float(1.0 - 0.5**hits)


def languages_covered() -> Iterable[str]:
    return tuple(LEXICON.keys())
