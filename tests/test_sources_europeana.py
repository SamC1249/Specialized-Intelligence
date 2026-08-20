"""Europeana adapter unit tests (offline)."""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.europeana import EuropeanaSource, _license_from_rights


def test_europeana_parse_extracts_video_records(load_json):
    raw = load_json("europeana/search_cooking.json")
    source = EuropeanaSource()
    query = SourceQuery(terms=["cooking"])
    records = source.parse(raw, query)

    assert len(records) == 3
    ids = {r.id for r in records}
    assert any(i.startswith("europeana:") for i in ids)


def test_europeana_parse_maps_licenses_and_hides_media_when_restricted(load_json):
    raw = load_json("europeana/search_cooking.json")
    records = EuropeanaSource().parse(raw, SourceQuery(terms=["cooking"]))
    by_title = {r.title.split(":")[0].lower(): r for r in records}

    pasta = next(r for r in records if "pasta" in r.title.lower())
    bread = next(r for r in records if "bread" in r.title.lower())
    restricted = next(r for r in records if "restricted" in r.title.lower())

    assert pasta.license is License.CC_BY_SA
    assert pasta.media_url is not None  # redistributable → keep media URL
    assert bread.license is License.PUBLIC_DOMAIN
    assert bread.media_url is not None
    assert restricted.license is License.UNKNOWN  # RS-* falls back to UNKNOWN
    assert restricted.media_url is None  # never expose media for UNKNOWN
    # sanity: our helper's key extraction did not double-count.
    assert len(by_title) == 3


def test_europeana_language_from_langaware(load_json):
    raw = load_json("europeana/search_cooking.json")
    records = EuropeanaSource().parse(raw, SourceQuery(terms=["cooking"]))
    langs = {r.title: r.language for r in records}
    # `language` field is a single string picked from the top-level array.
    assert set(langs.values()) <= {"it", "en"}


def test_license_from_rights_edge_cases():
    assert _license_from_rights(None) is License.UNKNOWN
    assert _license_from_rights([]) is License.UNKNOWN
    assert _license_from_rights("http://rightsstatements.org/vocab/InC/1.0/") is License.UNKNOWN
    assert _license_from_rights("http://creativecommons.org/licenses/by/4.0/") is License.CC_BY
    assert (
        _license_from_rights("https://creativecommons.org/licenses/by-sa/3.0/") is License.CC_BY_SA
    )
    assert (
        _license_from_rights("http://creativecommons.org/licenses/by-nc/4.0/") is License.RESTRICTED
    )
    assert _license_from_rights("https://creativecommons.org/publicdomain/zero/1.0/") is License.CC0
    assert (
        _license_from_rights("http://creativecommons.org/publicdomain/mark/1.0/")
        is License.PUBLIC_DOMAIN
    )
