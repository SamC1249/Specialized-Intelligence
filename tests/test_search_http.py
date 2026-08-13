"""Offline `search()` integration tests via respx.

Each adapter's `search()` performs a real HTTP call. Without these
tests, a silent regression in URL construction or parameter encoding
would only surface in production. respx intercepts httpx calls, so
these tests remain offline and CI-safe.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def query() -> SourceQuery:
    return SourceQuery(terms=["cooking", "recipe"], max_results=5)


@respx.mock
def test_wikimedia_search_hits_action_api_and_returns_records(query: SourceQuery):
    payload = json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text())
    route = respx.get("https://commons.wikimedia.org/w/api.php").mock(
        return_value=httpx.Response(200, json=payload)
    )
    records = WikimediaCommonsSource().search(query)
    records = list(records)
    assert route.called
    called_url = str(route.calls.last.request.url)
    assert "action=query" in called_url
    assert "generator=search" in called_url
    assert "gsrsearch=cooking+recipe+filetype%3Avideo" in called_url
    assert "gsrnamespace=6" in called_url
    assert any(r.source == "wikimedia" for r in records)


@respx.mock
def test_archive_org_search_uses_advancedsearch_endpoint(query: SourceQuery):
    payload = json.loads((FIXTURES / "archive_org/search_cooking.json").read_text())
    route = respx.get("https://archive.org/advancedsearch.php").mock(
        return_value=httpx.Response(200, json=payload)
    )
    records = ArchiveOrgSource().search(query)
    records = list(records)
    assert route.called
    called_url = str(route.calls.last.request.url)
    assert "output=json" in called_url
    assert "mediatype%3Amovies" in called_url
    assert "%22cooking%22" in called_url and "%22recipe%22" in called_url
    assert any(r.source == "archive_org" for r in records)


@respx.mock
def test_peertube_search_calls_each_instance(query: SourceQuery):
    payload = json.loads((FIXTURES / "peertube/search_cooking.json").read_text())
    for instance in ("https://framatube.org", "https://video.blender.org", "https://tilvids.com"):
        respx.get(f"{instance}/api/v1/search/videos").mock(
            return_value=httpx.Response(200, json=payload)
        )
    records = list(PeerTubeSource().search(query))
    hosts = {r.provenance.query for r in records}
    assert hosts  # something came through
    slugs = {r.source for r in records}
    assert slugs == {"peertube"}


@respx.mock
def test_peertube_search_survives_partial_failures(query: SourceQuery):
    payload = json.loads((FIXTURES / "peertube/search_cooking.json").read_text())
    respx.get("https://framatube.org/api/v1/search/videos").mock(return_value=httpx.Response(500))
    respx.get("https://video.blender.org/api/v1/search/videos").mock(
        return_value=httpx.Response(200, json=payload)
    )
    respx.get("https://tilvids.com/api/v1/search/videos").mock(
        return_value=httpx.Response(200, json=payload)
    )
    records = list(PeerTubeSource().search(query))
    assert records
    assert all(r.source == "peertube" for r in records)


@respx.mock
def test_wikimedia_search_bubbles_up_http_errors():
    respx.get("https://commons.wikimedia.org/w/api.php").mock(return_value=httpx.Response(500))
    src = WikimediaCommonsSource()
    with pytest.raises(httpx.HTTPStatusError):
        list(src.search(SourceQuery(terms=["cooking"], max_results=1)))
