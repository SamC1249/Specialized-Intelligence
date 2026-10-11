from __future__ import annotations

from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.flickr import ALLOWED_LICENSE_CODES, FlickrCCSource


def test_flickr_parse_keeps_only_videos_with_clean_licenses(fixtures_dir: Path, load_json):
    raw = load_json("flickr/search_cooking.json")
    records = FlickrCCSource().parse(raw, SourceQuery(terms=["cooking"]))

    # Photo and the BY-NC entry drop out; 3 CC-permissive videos remain.
    assert len(records) == 3
    assert {r.license for r in records} == {License.CC_BY, License.CC_BY_SA, License.PUBLIC_DOMAIN}
    for r in records:
        assert r.source == "flickr"
        assert r.license.is_redistributable
        assert r.media_url is not None


def test_flickr_license_codes_only_whitelist_clean(load_json):
    raw = load_json("flickr/search_cooking.json")
    kept = FlickrCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    assert all(
        int(r.source_native_id in {"52123456789", "52987654321", "53111222333"}) for r in kept
    )
    # Sanity: allowed codes are a subset of the CC-permissive map.
    assert set(ALLOWED_LICENSE_CODES) == {4, 5, 7, 8, 9, 10}


def test_flickr_parse_handles_empty_input():
    assert FlickrCCSource().parse({}, SourceQuery(terms=["x"])) == []
    assert FlickrCCSource().parse("bogus", SourceQuery(terms=["x"])) == []


def test_flickr_search_without_key_is_a_no_op(monkeypatch):
    monkeypatch.delenv("FLICKR_API_KEY", raising=False)
    assert list(FlickrCCSource().search(SourceQuery(terms=["cooking"]))) == []
