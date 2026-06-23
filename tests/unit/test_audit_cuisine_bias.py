from __future__ import annotations

from specint.audit import audit_records, classify_cuisine, detect_language_iso2
from specint.records import License, Provenance, VideoRecord


def _rec(**kw) -> VideoRecord:
    base = {
        "id": "x:1",
        "source": "wikimedia",
        "source_native_id": "1",
        "url": "https://example.org/p",
        "title": "Pasta carbonara recipe",
        "description": "How to cook the classic Italian pasta with eggs and pancetta.",
        "license": License.CC_BY,
        "provenance": Provenance(extractor="t"),
        "duration_s": 120.0,
    }
    base.update(kw)
    return VideoRecord(**base)


def test_classify_cuisine_italian():
    assert classify_cuisine("Pasta carbonara with parmesan") == "italian"


def test_classify_cuisine_japanese():
    assert classify_cuisine("How to make sushi at home") == "japanese"


def test_classify_cuisine_unknown_text_is_other():
    assert classify_cuisine("a generic title") == "other"


def test_classify_cuisine_empty_is_unknown():
    assert classify_cuisine("") == "unknown"


def test_detect_language_english():
    assert detect_language_iso2("How to cook the classic Italian pasta with eggs") == "en"


def test_detect_language_japanese():
    assert detect_language_iso2("カレーのレシピと作り方") == "ja"


def test_detect_language_und_on_empty():
    assert detect_language_iso2("") == "und"


def test_audit_report_aggregates():
    r1 = _rec(id="a", title="Pasta carbonara", description="Italian recipe with eggs")
    r2 = _rec(
        id="b",
        title="Sushi rolls",
        description="Japanese cuisine basics — how to roll sushi at home",
        language="ja",
    )
    r3 = _rec(
        id="c",
        title="Tacos al pastor",
        description="Mexican taco recipe; cook the pork carefully",
        duration_s=240.0,
    )
    report = audit_records([r1, r2, r3])
    d = report.to_dict()
    assert d["n_records"] == 3
    assert d["n_with_language_declared"] == 1
    assert d["cuisine_counts"]["italian"] >= 1
    assert d["cuisine_counts"]["japanese"] >= 1
    assert d["cuisine_counts"]["mexican"] >= 1
    assert d["language_counts"].get("ja", 0) >= 1
    assert d["language_counts"].get("en", 0) >= 1
    assert d["source_counts"]["wikimedia"] == 3
    assert d["license_counts"]["CC-BY"] == 3
    assert d["duration_total_s"] == 480.0


def test_audit_report_is_deterministic():
    r1 = _rec(id="a")
    r2 = _rec(id="b", title="Sushi rolls")
    d1 = audit_records([r1, r2]).to_dict()
    d2 = audit_records([r1, r2]).to_dict()
    assert d1 == d2
