from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import (
    YouTubeCCSource,
    _license_from_status,
    _parse_youtube_duration,
)


def test_parse_youtube_duration():
    assert _parse_youtube_duration("PT5M12S") == 312.0
    assert _parse_youtube_duration("PT1H") == 3600.0
    assert _parse_youtube_duration("PT0S") is None
    assert _parse_youtube_duration(None) is None
    assert _parse_youtube_duration("garbage") is None


def test_license_from_status():
    assert _license_from_status("creativeCommon") is License.CC_BY
    assert _license_from_status("youtube") is License.UNKNOWN
    assert _license_from_status(None) is License.UNKNOWN


def test_youtube_cc_parse_returns_only_cc_records_with_no_media_url(load_json):
    raw = load_json("youtube_cc/search_cooking.json")
    src = YouTubeCCSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=25))

    assert len(records) == 3
    licenses = {r.id: r.license for r in records}
    assert licenses["youtube_cc:aBcDefGhIjK"] is License.CC_BY
    assert licenses["youtube_cc:lMnOpQrStUv"] is License.UNKNOWN
    assert licenses["youtube_cc:wXyZ012345"] is License.CC_BY

    for r in records:
        assert r.media_url is None
        assert str(r.url).startswith("https://www.youtube.com/watch?v=")


def test_youtube_cc_parse_extracts_metadata(load_json):
    raw = load_json("youtube_cc/search_cooking.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    by_id = {r.source_native_id: r for r in records}

    r = by_id["aBcDefGhIjK"]
    assert r.duration_s == 312.0
    assert r.height == 720
    assert r.language == "en"
    assert r.author == "Public Domain Kitchen"
    assert "pasta" in r.keywords

    r_fr = by_id["wXyZ012345"]
    assert r_fr.language == "fr"


def test_youtube_cc_parse_handles_bad_input():
    src = YouTubeCCSource()
    assert src.parse({}, SourceQuery(terms=["x"])) == []
    assert src.parse({"items": []}, SourceQuery(terms=["x"])) == []
    assert src.parse({"items": [{}]}, SourceQuery(terms=["x"])) == []


def test_youtube_cc_search_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    src = YouTubeCCSource()
    result = list(src.search(SourceQuery(terms=["cooking"])))
    assert result == []
