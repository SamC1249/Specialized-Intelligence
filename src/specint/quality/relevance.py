"""Multilingual cooking-relevance scoring.

Pure, deterministic, metadata-only. Given a `VideoRecord`, return a float
in `[0, 1]` reflecting how likely the record is actually about cooking.
Signals:
  - cooking-keyword hits in title + description + declared keywords;
  - multilingual term coverage (we count hits in *any* known language);
  - a tiny negative list (news/music/sports) that forces the score down
    when the title is clearly off-topic.

This is deliberately lower-precision than a classifier: we only need to
re-rank a huge candidate list without downloading anything.
"""

from __future__ import annotations

import re
import unicodedata

from specint.records import VideoRecord

_POSITIVE: dict[str, frozenset[str]] = {
    "en": frozenset(
        {
            "cook",
            "cooking",
            "recipe",
            "bake",
            "baking",
            "roast",
            "fry",
            "simmer",
            "saute",
            "sauté",
            "kitchen",
            "chef",
            "pasta",
            "bread",
            "sauce",
            "soup",
            "stew",
            "knife",
            "chop",
            "mince",
            "dice",
            "braise",
            "boil",
            "grill",
            "food",
            "dinner",
            "breakfast",
            "lunch",
            "ferment",
            "fermentation",
            "dough",
            "butter",
            "garlic",
        }
    ),
    "es": frozenset(
        {
            "cocina",
            "cocinar",
            "receta",
            "hornear",
            "asado",
            "freir",
            "freír",
            "sopa",
            "guiso",
            "pan",
            "salsa",
            "picar",
            "hervir",
            "cuchillo",
            "pasta",
            "comida",
        }
    ),
    "fr": frozenset(
        {
            "cuisine",
            "cuisiner",
            "recette",
            "cuire",
            "four",
            "poêle",
            "soupe",
            "ragoût",
            "pain",
            "sauce",
            "couteau",
            "pâtes",
            "beurre",
            "ail",
            "repas",
            "chef",
        }
    ),
    "de": frozenset(
        {
            "kochen",
            "küche",
            "rezept",
            "backen",
            "braten",
            "suppe",
            "eintopf",
            "brot",
            "soße",
            "messer",
            "nudeln",
            "butter",
            "knoblauch",
            "essen",
        }
    ),
    "it": frozenset(
        {
            "cucina",
            "cucinare",
            "ricetta",
            "forno",
            "pasta",
            "zuppa",
            "stufato",
            "pane",
            "salsa",
            "coltello",
            "burro",
            "aglio",
            "cibo",
        }
    ),
    "pt": frozenset(
        {
            "cozinha",
            "cozinhar",
            "receita",
            "forno",
            "sopa",
            "ensopado",
            "pão",
            "molho",
            "faca",
            "massa",
            "manteiga",
            "alho",
            "comida",
        }
    ),
}

_NEGATIVE = frozenset(
    {
        "earthquake",
        "election",
        "goal",
        "concert",
        "match",
        "race",
        "crash",
        "trailer",
        "gameplay",
        "esports",
        "stock",
        "finance",
        "crypto",
        "landscape",
    }
)

_WORD_RE = re.compile(r"[\w\u00c0-\u024f]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKC", text).lower()
    return _WORD_RE.findall(folded)


def cooking_relevance(record: VideoRecord) -> float:
    """Return a value in [0, 1]. Pure, metadata-only."""
    parts = [record.title or "", record.description or ""]
    parts.extend(record.keywords or [])
    parts.extend(record.recipe_steps or [])
    text = " ".join(parts)
    if not text.strip():
        return 0.0

    tokens = set(_tokens(text))
    if not tokens:
        return 0.0

    positive_hits = 0
    for vocab in _POSITIVE.values():
        positive_hits += len(tokens & vocab)
    negative_hits = len(tokens & _NEGATIVE)

    if positive_hits == 0:
        return 0.0
    # Saturate at 3 hits; penalise negatives but never below 0.
    score = min(1.0, positive_hits / 3.0) - 0.25 * negative_hits
    return max(0.0, min(1.0, score))
