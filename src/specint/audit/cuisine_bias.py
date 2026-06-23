"""Cuisine / language / corpus-bias audit (Adversarial-Agent plan §7.3).

HowTo100M is heavily English/Western; our license-clean substitute graph
is *probably worse* on the same axis. This module produces a deterministic,
JSON-serialisable audit report from a set of `VideoRecord`s — no network,
no ML, pure-Python keyword tables — so the bias picture lands in CI
artifacts alongside the source-comparison report.

What this is NOT:
  * Not a language model. It is a keyword / pattern classifier; for
    English-only corpora it works well, and it always emits an `unknown`
    bucket so we never silently mislabel.
  * Not a substitute for a human-reviewed sampled audit. It is a
    *systematic, comparable* signal we can run cheaply on every batch.

Inputs / outputs:
  * `classify_cuisine(text: str) -> str`  (one of CUISINE_PATTERNS or "other")
  * `detect_language_iso2(text: str) -> str`  (e.g. "en", "ja", "und")
  * `audit_records(records) -> AuditReport`

`AuditReport.to_dict()` is stable across runs given the same input order.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from specint.records import VideoRecord

CUISINE_PATTERNS: dict[str, tuple[str, ...]] = {
    "italian": ("pasta", "risotto", "pizza", "carbonara", "lasagna", "ragu", "tiramisu"),
    "french": (
        "baguette",
        "croissant",
        "ratatouille",
        "souffle",
        "creme brulee",
        "tarte",
        "bouillabaisse",
    ),
    "japanese": ("sushi", "ramen", "tempura", "miso", "udon", "soba", "okonomiyaki", "yakitori"),
    "chinese": (
        "dumpling",
        "stir fry",
        "stir-fry",
        "fried rice",
        "kung pao",
        "mapo",
        "bao",
        "wonton",
    ),
    "indian": ("curry", "biryani", "tandoori", "masala", "dal", "naan", "samosa", "paneer"),
    "mexican": ("taco", "burrito", "enchilada", "quesadilla", "salsa", "guacamole", "mole"),
    "middle_eastern": ("hummus", "falafel", "shawarma", "tabbouleh", "kebab", "baba ghanoush"),
    "thai": ("pad thai", "tom yum", "green curry", "satay", "som tam"),
    "korean": ("kimchi", "bibimbap", "bulgogi", "tteokbokki", "japchae"),
    "american": ("burger", "barbecue", "bbq", "mac and cheese", "grilled cheese", "meatloaf"),
    "baking": ("cake", "cookie", "bread", "pie", "muffin", "scone", "brownie", "pastry"),
    "vegan": ("vegan", "plant-based", "plant based"),
}

LANG_HINTS: dict[str, tuple[str, ...]] = {
    "en": (" the ", " and ", " with ", " for ", " how ", " to ", "recipe"),
    "es": (" el ", " la ", " con ", " para ", " como ", "receta"),
    "fr": (" le ", " la ", " avec ", " pour ", " comment ", "recette"),
    "de": (" der ", " die ", " das ", " mit ", "rezept"),
    "it": (" il ", " la ", " con ", " per ", "ricetta"),
    "pt": (" o ", " a ", " com ", " para ", "receita"),
    "ja": ("レシピ", "作り方", "料理"),
    "zh": ("食谱", "做法", "菜谱"),
    "ko": ("레시피", "요리", "만들기"),
}


def _join_text(record: VideoRecord) -> str:
    parts = [record.title, record.description, " ".join(record.keywords)]
    return " ".join(p for p in parts if p).lower()


def classify_cuisine(text: str) -> str:
    if not text:
        return "unknown"
    hits = Counter()
    lowered = text.lower()
    for cuisine, patterns in CUISINE_PATTERNS.items():
        for needle in patterns:
            if needle in lowered:
                hits[cuisine] += 1
    if not hits:
        return "other"
    return hits.most_common(1)[0][0]


def detect_language_iso2(text: str) -> str:
    if not text:
        return "und"
    padded = " " + text.lower() + " "
    scores: Counter[str] = Counter()
    for lang, hints in LANG_HINTS.items():
        for h in hints:
            if h in padded:
                scores[lang] += 1
    if not scores:
        return "und"
    return scores.most_common(1)[0][0]


@dataclass
class AuditReport:
    n_records: int = 0
    n_with_language_declared: int = 0
    cuisine_counts: dict[str, int] = field(default_factory=dict)
    language_counts: dict[str, int] = field(default_factory=dict)
    source_counts: dict[str, int] = field(default_factory=dict)
    license_counts: dict[str, int] = field(default_factory=dict)
    duration_total_s: float = 0.0
    duration_by_cuisine_s: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key in (
            "cuisine_counts",
            "language_counts",
            "source_counts",
            "license_counts",
            "duration_by_cuisine_s",
        ):
            d[key] = dict(sorted(d[key].items()))
        return d


def audit_records(records: Iterable[VideoRecord]) -> AuditReport:
    report = AuditReport()
    cuisine = Counter()
    lang = Counter()
    src = Counter()
    lic = Counter()
    by_cuisine_dur: Counter = Counter()
    for r in records:
        report.n_records += 1
        text = _join_text(r)
        c = classify_cuisine(text)
        cuisine[c] += 1
        declared = r.language
        if declared:
            report.n_with_language_declared += 1
            inferred = declared
        else:
            inferred = detect_language_iso2(text)
        lang[inferred] += 1
        src[r.source] += 1
        lic[r.license.value] += 1
        if r.duration_s:
            report.duration_total_s += float(r.duration_s)
            by_cuisine_dur[c] += float(r.duration_s)

    report.cuisine_counts = dict(cuisine)
    report.language_counts = dict(lang)
    report.source_counts = dict(src)
    report.license_counts = dict(lic)
    report.duration_by_cuisine_s = dict(by_cuisine_dur)
    return report
