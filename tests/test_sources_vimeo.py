from __future__ import annotations

from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.vimeo import VimeoCCSource


def test_vimeo_parse_filters_non_redistributable(fixtures_dir: Path, load_json):
    raw = load_json("vimeo/search_cooking.json")
    query = SourceQuery(terms=["cooking"], max_results=25)
    records = VimeoCCSource().parse(raw, query)

    assert len(records) == 3  # the by-nc-nd clip is dropped
    assert all(r.source == "vimeo" for r in records)
    assert {r.license for r in records} == {License.CC_BY, License.CC0, License.CC_BY_SA}


def test_vimeo_parse_populates_media_url_only_when_license_allows(load_json):
    raw = load_json("vimeo/search_cooking.json")
    records = VimeoCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    for r in records:
        if r.license.is_redistributable:
            assert r.media_url is not None, r
        else:
            assert r.media_url is None, r


def test_vimeo_parse_prefers_highest_resolution_progressive_file(load_json):
    raw = load_json("vimeo/search_cooking.json")
    records = VimeoCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    cc0 = next(r for r in records if r.license is License.CC0)
    assert cc0.height == 2160
    assert "4k" in str(cc0.media_url)


def test_vimeo_parse_ignores_bad_input():
    assert VimeoCCSource().parse("not a dict", SourceQuery(terms=["x"])) == []
    assert VimeoCCSource().parse({"data": []}, SourceQuery(terms=["x"])) == []


def test_vimeo_search_without_token_is_a_no_op(monkeypatch):
    monkeypatch.delenv("VIMEO_API_TOKEN", raising=False)
    records = list(VimeoCCSource().search(SourceQuery(terms=["cooking"])))
    assert records == []
