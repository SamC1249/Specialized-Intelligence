"""Domain registry for the "difficult video" harvest.

Every domain declares:

- ``slug``: short identifier used on the CLI (``--domain cooking``).
- ``seed_terms``: search terms fed to source adapters.
- ``verb_vocab``: action verbs whose presence in metadata predicts
  procedural, world-model-useful content.
- ``blocklist_terms``: substrings whose presence in title/description
  strongly signals *non*-procedural media (trailers, montages, ...).

The registry decouples "what we look for" from "where we look".
Adding a new domain never touches ``sources/``; adding a new source
never touches ``domains``.

Vocabulary policy:
  Verbs are lowercased ASCII stems. We deliberately do not stem or
  lemmatize — we keep a curated allowlist so that ``chop`` matches
  ``chop``, ``chops``, ``chopped``, ``chopping`` by prefix contain.
  Multilingual verb vocabs are a follow-up (see 2026-07-11 plan).
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_BLOCKLIST: tuple[str, ...] = (
    "trailer",
    "teaser",
    "montage",
    "compilation",
    "aftermovie",
    "highlights",
    "reel",
    "sizzle",
)


@dataclass(frozen=True)
class Domain:
    slug: str
    seed_terms: tuple[str, ...]
    verb_vocab: tuple[str, ...]
    blocklist_terms: tuple[str, ...] = _DEFAULT_BLOCKLIST


COOKING = Domain(
    slug="cooking",
    seed_terms=("cooking", "recipe", "kitchen", "how to cook"),
    verb_vocab=(
        "chop",
        "dice",
        "mince",
        "slice",
        "peel",
        "grate",
        "saute",
        "sauté",
        "fry",
        "simmer",
        "boil",
        "roast",
        "bake",
        "grill",
        "whisk",
        "fold",
        "knead",
        "season",
        "deglaze",
        "reduce",
        "marinate",
        "sear",
        "steam",
        "poach",
        "stir",
        "toss",
        "drizzle",
        "sprinkle",
        "garnish",
    ),
)

SURGERY = Domain(
    slug="surgery",
    seed_terms=("surgery", "surgical procedure", "operating room", "laparoscopic"),
    verb_vocab=(
        "incise",
        "suture",
        "cauterize",
        "clamp",
        "resect",
        "excise",
        "ligate",
        "dissect",
        "retract",
        "aspirate",
        "irrigate",
        "anastomose",
        "cannulate",
        "intubate",
        "palpate",
        "biopsy",
        "sample",
    ),
)

LAB = Domain(
    slug="lab",
    seed_terms=("laboratory", "lab experiment", "chemistry demonstration", "wet lab"),
    verb_vocab=(
        "pipette",
        "titrate",
        "centrifuge",
        "vortex",
        "incubate",
        "aliquot",
        "dilute",
        "buffer",
        "extract",
        "elute",
        "precipitate",
        "filter",
        "weigh",
        "calibrate",
        "measure",
        "record",
    ),
)

SPORTS = Domain(
    slug="sports",
    seed_terms=("sports training", "athletic drill", "coaching demonstration"),
    verb_vocab=(
        "kick",
        "throw",
        "catch",
        "run",
        "sprint",
        "jump",
        "shoot",
        "pass",
        "block",
        "tackle",
        "dribble",
        "serve",
        "spike",
        "swing",
        "stroke",
        "row",
        "climb",
        "lift",
        "squat",
        "press",
    ),
)

MANUFACTURING = Domain(
    slug="manufacturing",
    seed_terms=("manufacturing process", "assembly line", "machining", "workshop"),
    verb_vocab=(
        "weld",
        "solder",
        "drill",
        "mill",
        "lathe",
        "turn",
        "grind",
        "polish",
        "sand",
        "cut",
        "bend",
        "fold",
        "rivet",
        "screw",
        "bolt",
        "clamp",
        "align",
        "calibrate",
        "assemble",
        "install",
        "inspect",
        "measure",
    ),
)


REGISTRY: dict[str, Domain] = {d.slug: d for d in (COOKING, SURGERY, LAB, SPORTS, MANUFACTURING)}


def get(slug: str) -> Domain:
    if slug not in REGISTRY:
        raise KeyError(f"unknown domain {slug!r}; known domains: {sorted(REGISTRY)}")
    return REGISTRY[slug]


def domain_slugs() -> list[str]:
    return sorted(REGISTRY)


# English inflection suffixes, including doubled-consonant forms so that
# "chop" matches "chopped"/"chopping" and "stir" matches "stirred".
_INFLECTION_SUFFIXES: tuple[str, ...] = (
    "",
    "s",
    "es",
    "d",
    "ed",
    "ing",
    "ped",
    "ping",
    "ted",
    "ting",
    "ned",
    "ning",
    "led",
    "ling",
    "ked",
    "king",
    "med",
    "ming",
    "red",
    "ring",
    "ged",
    "ging",
)


def verb_hit_count(text: str, vocab: tuple[str, ...]) -> int:
    """Count occurrences of any verb in ``vocab`` as a whole-word match with
    common English inflections (``s``, ``ed``, ``d``, ``ing``, ``es``).

    ``"chop"`` matches ``chop``, ``chops``, ``chopped``, ``chopping``, but
    not ``chopstick`` — the trailing characters must exactly form one of
    ``_INFLECTION_SUFFIXES`` and must be followed by a non-letter (or
    end-of-string).
    """
    if not text:
        return 0
    hay = text.lower()
    n = len(hay)
    hits = 0
    for verb in vocab:
        v = verb.lower()
        vlen = len(v)
        start = 0
        while True:
            idx = hay.find(v, start)
            if idx < 0:
                break
            before_ok = idx == 0 or not hay[idx - 1].isalpha()
            if before_ok:
                for suf in _INFLECTION_SUFFIXES:
                    end = idx + vlen + len(suf)
                    if end > n:
                        continue
                    if suf and hay[idx + vlen : end] != suf:
                        continue
                    after_ok = end == n or not hay[end].isalpha()
                    if after_ok:
                        hits += 1
                        break
            start = idx + max(1, vlen)
    return hits


def contains_blocklisted(text: str, blocklist: tuple[str, ...]) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(term in t for term in blocklist)


@dataclass(frozen=True)
class _DomainField:
    slug: str


DEFAULT_DOMAIN_SLUG = "cooking"
