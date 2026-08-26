"""Unit tests for the metadata-only YouTube CC-BY adapter (W10)."""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCCSource


def test_youtube_cc_parse_filters_non_cc_and_keeps_metadata(load_json):
    raw = load_json("youtube_cc/search_cooking.json")
    src = YouTubeCCSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=25))

    assert {r.source for r in records} == {"youtube_cc"}
    ids = {r.source_native_id for r in records}
    assert ids == {"abc12345678", "def87654321"}
    assert "restricted999" not in ids

    by_id = {r.source_native_id: r for r in records}

    carb = by_id["abc12345678"]
    assert carb.license is License.CC_BY
    assert carb.duration_s == 8 * 60 + 12
    assert carb.height == 720
    assert carb.author == "Open Kitchen"
    # AGENTS.md rule #1 — metadata only, never a media URL for YouTube.
    assert carb.media_url is None
    assert str(carb.url) == "https://www.youtube.com/watch?v=abc12345678"

    bread = by_id["def87654321"]
    assert bread.duration_s == 42 * 60 + 7
    assert "sourdough" in bread.keywords


def test_youtube_cc_parse_handles_empty():
    src = YouTubeCCSource()
    assert src.parse({}, SourceQuery(terms=["x"])) == []
    assert src.parse({"items": []}, SourceQuery(terms=["x"])) == []


def test_youtube_cc_search_offline_by_default(monkeypatch):
    """Without env opt-in the adapter must not touch the network."""
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    src = YouTubeCCSource()
    assert list(src.search(SourceQuery(terms=["cooking"]))) == []
