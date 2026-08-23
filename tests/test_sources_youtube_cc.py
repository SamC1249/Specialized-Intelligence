from __future__ import annotations

import os
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import (
    YouTubeCreativeCommonsSource,
    _parse_iso8601_duration,
)


def test_youtube_cc_parse_filters_non_cc(load_json):
    payload = load_json("youtube_cc/search_cc_recipe.json")
    query = SourceQuery(terms=["cooking"], max_results=25)
    records = YouTubeCreativeCommonsSource().parse(payload, query)
    ids = {r.source_native_id for r in records}
    assert "abc12345678" in ids
    assert "def87654321" in ids
    assert "zzznotcc9999" not in ids
    for r in records:
        assert r.license is License.CC_BY
        assert r.media_url is None
        assert str(r.url).startswith("https://www.youtube.com/watch?v=")


def test_youtube_cc_parse_extracts_duration(load_json):
    payload = load_json("youtube_cc/search_cc_recipe.json")
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_id = {r.source_native_id: r for r in YouTubeCreativeCommonsSource().parse(payload, query)}
    assert by_id["abc12345678"].duration_s == 8 * 60 + 42
    assert by_id["def87654321"].duration_s == 12 * 60 + 3


def test_parse_iso8601_duration_edge_cases():
    assert _parse_iso8601_duration("PT1H2M3S") == 3723
    assert _parse_iso8601_duration("PT45S") == 45
    assert _parse_iso8601_duration("PT0S") == 0
    assert _parse_iso8601_duration(None) is None
    assert _parse_iso8601_duration("garbage") is None


def test_search_without_api_key_is_empty(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    out = list(YouTubeCreativeCommonsSource().search(SourceQuery(terms=["cooking"])))
    assert out == []


def test_fixture_lives_in_repo():
    p = Path(__file__).parent / "fixtures" / "youtube_cc" / "search_cc_recipe.json"
    assert p.exists()
    assert os.path.getsize(p) > 0
