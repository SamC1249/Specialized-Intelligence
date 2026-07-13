# ruff: noqa: RUF001
"""Tiny offline language identifier.

A character-trigram classifier over a fixed set of languages. The
frequency tables are compiled inline from short public-domain sentences
so we do not ship a heavyweight model file. Accuracy is a signal, not a
guarantee — we only need to distinguish the ~10 largest languages likely
to appear in cooking-video metadata (English, Spanish, French, German,
Italian, Portuguese, Japanese, Chinese, Arabic, Russian).

Every public function is pure and deterministic. The scoring layer uses
`confidence` as a quality-component input; downstream consumers can also
read `detect()` directly to fill `VideoRecord.language`.

Design notes:
  - Confidence is scaled by input length so a 3-word title does not
    receive a 1.0 (see H3 in `docs/plan-2026-07-13.md`).
  - CJK scripts short-circuit the trigram vote via Unicode-block checks.
  - `SUPPORTED` is the closed set; anything else returns `None`.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable

SUPPORTED: tuple[str, ...] = (
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "ja",
    "zh",
    "ar",
    "ru",
)


_SAMPLES: dict[str, str] = {
    "en": (
        "the quick brown fox jumps over the lazy dog and then makes a "
        "cup of tea while the pasta boils on the stove and the onions "
        "caramelise slowly in the pan with butter and salt to taste"
    ),
    "es": (
        "la receta tradicional de arroz con pollo se prepara con "
        "cebolla ajo pimiento verde y tomate maduro cocinado a fuego "
        "lento hasta que el caldo se reduzca y el arroz quede suelto"
    ),
    "fr": (
        "faites revenir les oignons emincés dans une poêle avec un "
        "peu de beurre puis ajoutez l ail écrasé le vin blanc sec et "
        "laissez mijoter à feu doux pendant vingt minutes environ"
    ),
    "de": (
        "die zwiebeln fein hacken und in einer pfanne mit butter "
        "goldbraun anbraten dann das mehl darüberstäuben mit brühe "
        "ablöschen und bei mittlerer hitze weiterkochen bis alles bindet"
    ),
    "it": (
        "in una pentola capiente far soffriggere la cipolla tritata "
        "con olio extravergine di oliva quindi unire il pomodoro e "
        "il basilico e cuocere a fuoco lento per circa trenta minuti"
    ),
    "pt": (
        "numa panela grande refogue a cebola picada em azeite quente "
        "adicione o alho os tomates maduros e um pouco de sal cozinhe "
        "em fogo baixo até que o molho engrosse e fique saboroso"
    ),
    "ru": (
        "в глубокой сковороде обжарьте лук и морковь до золотистого "
        "цвета затем добавьте томатную пасту чеснок и специи по вкусу "
        "тушите под крышкой около двадцати минут перед подачей"
    ),
    "ar": (
        "في مقلاة كبيرة ضعي البصل المفروم مع زيت الزيتون واقلبيه على "
        "نار متوسطة ثم أضيفي الثوم والطماطم واتركيه على نار هادئة "
        "حتى ينضج تماما قبل التقديم مع الأرز الأبيض"
    ),
    "ja": (
        "玉ねぎとにんじんを細かく切り、フライパンに油を入れて中火で"
        "炒めます。にんにくと生姜を加え、香りが立ったら鶏肉を入れて"
        "表面が色付くまで焼き、醤油と味醂を加えて煮込みます"
    ),
    "zh": (
        "先把洋葱切成小丁，锅里放油，大火加热，然后放入蒜末爆香，"
        "加入西红柿翻炒均匀，加一点糖和盐调味，最后倒入清水盖上"
        "锅盖，用小火慢炖二十分钟，直到汤汁浓稠"
    ),
}


_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = _WORD_RE.findall(text)
    return " ".join(tokens)


def _trigrams(text: str) -> list[str]:
    padded = f"  {text}  "
    return [padded[i : i + 3] for i in range(len(padded) - 2)]


def _profile(text: str) -> Counter[str]:
    return Counter(_trigrams(_normalise(text)))


_PROFILES: dict[str, Counter[str]] = {lang: _profile(sample) for lang, sample in _SAMPLES.items()}


def _has_cjk(text: str) -> str | None:
    for ch in text:
        cp = ord(ch)
        if 0x3040 <= cp <= 0x30FF or 0xFF66 <= cp <= 0xFF9D:
            return "ja"
        if 0x4E00 <= cp <= 0x9FFF:
            has_kana = any(0x3040 <= ord(c) <= 0x30FF for c in text)
            return "ja" if has_kana else "zh"
        if 0x0600 <= cp <= 0x06FF:
            return "ar"
        if 0x0400 <= cp <= 0x04FF:
            return "ru"
    return None


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def detect(text: str) -> str | None:
    """Return best-guess BCP-47 language code or `None` when input is empty."""
    if not text or not text.strip():
        return None
    script_hint = _has_cjk(text)
    if script_hint is not None:
        return script_hint
    profile = _profile(text)
    if not profile:
        return None
    scored = sorted(
        ((lang, _cosine(profile, ref)) for lang, ref in _PROFILES.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    top_lang, top_score = scored[0]
    if top_score <= 0.0:
        return None
    return top_lang


def confidence(text: str) -> float:
    """Length-aware confidence in [0, 1].

    Short strings can never earn full confidence (H3 in the plan). The
    length scaling saturates around ~120 characters.
    """
    if not text or not text.strip():
        return 0.0
    script_hint = _has_cjk(text)
    length = len(_normalise(text))
    length_factor = min(1.0, length / 120.0)
    if script_hint is not None:
        return 0.6 + 0.4 * length_factor
    profile = _profile(text)
    if not profile:
        return 0.0
    scores = sorted(
        (_cosine(profile, ref) for ref in _PROFILES.values()),
        reverse=True,
    )
    top = scores[0]
    runner_up = scores[1] if len(scores) > 1 else 0.0
    margin = max(0.0, top - runner_up)
    raw = min(1.0, top * 0.7 + margin * 3.0)
    return raw * length_factor


def detect_many(texts: Iterable[str]) -> list[str | None]:
    return [detect(t) for t in texts]
