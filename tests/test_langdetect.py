from __future__ import annotations

from datetime import UTC, datetime

from specint.quality.langdetect import backfill_languages, detect
from specint.records import Provenance, VideoRecord


def _rec(title: str, description: str = "", language: str | None = None) -> VideoRecord:
    return VideoRecord(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/a",
        title=title,
        description=description,
        language=language,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query="q"),
    )


def test_detect_english():
    assert detect("How to make the best pasta recipe with garlic and butter") == "en"


def test_detect_spanish():
    assert detect("Cómo hacer una receta de cocina fácil con arroz y pollo") == "es"


def test_detect_french():
    assert detect("Comment faire la recette de cuisine avec du beurre et des œufs") == "fr"


def test_detect_returns_none_for_short_text():
    assert detect("hi") is None


def test_backfill_languages_only_fills_when_missing():
    r_missing = _rec("How to make sourdough bread the easy way with the oven")
    r_present = _rec("こんにちは", language="ja")
    out = backfill_languages([r_missing, r_present])
    assert out[0].language == "en"
    assert out[1].language == "ja"
