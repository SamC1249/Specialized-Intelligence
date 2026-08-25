"""YouTube CC adapter — parses fixtures, never touches the network."""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCreativeCommonsSource


def test_youtube_cc_only_upgrades_when_status_and_licensedcontent_agree(load_json):
    raw = load_json("youtube_cc/search_cooking.json")
    records = YouTubeCreativeCommonsSource().parse(raw, SourceQuery(terms=["cooking"]))
    by_id = {r.source_native_id: r for r in records}

    assert by_id["cc_clean_1"].license is License.CC_BY
    assert by_id["cc_clean_1"].media_url is None  # never redistribute media
    assert by_id["cc_clean_1"].duration_s == 4 * 60 + 32

    assert by_id["cc_contradict_2"].license is License.UNKNOWN
    assert by_id["std_license_3"].license is License.UNKNOWN


def test_youtube_cc_never_sets_media_url(load_json):
    records = YouTubeCreativeCommonsSource().parse(
        load_json("youtube_cc/search_cooking.json"), SourceQuery(terms=["cooking"])
    )
    assert records
    assert all(r.media_url is None for r in records)


def test_youtube_cc_search_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    source = YouTubeCreativeCommonsSource()
    assert list(source.search(SourceQuery(terms=["cooking"]))) == []
