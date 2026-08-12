"""Offline unit tests for YouTubeCCSource."""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.youtube import YouTubeCCSource


def test_parse_keeps_only_creative_commons(load_json):
    raw = load_json("youtube/videos_list.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    ids = [r.source_native_id for r in records]
    assert ids == ["abc123XYZ_1", "def456UVW_2"]
    assert all(r.license is License.CC_BY for r in records)


def test_parse_never_sets_media_url(load_json):
    raw = load_json("youtube/videos_list.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    assert all(r.media_url is None for r in records)


def test_parse_extracts_duration_and_resolution(load_json):
    raw = load_json("youtube/videos_list.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    first = records[0]
    assert first.duration_s == 492.0  # 8m12s
    assert first.height == 720
    assert first.language == "en"
    assert "cooking" in first.keywords


def test_parse_handles_empty_or_missing_gracefully():
    src = YouTubeCCSource()
    assert src.parse({}, SourceQuery(terms=["x"])) == []
    assert src.parse({"items": []}, SourceQuery(terms=["x"])) == []
    assert src.parse("not a dict", SourceQuery(terms=["x"])) == []


def test_search_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    assert list(YouTubeCCSource().search(SourceQuery(terms=["cooking"]))) == []
