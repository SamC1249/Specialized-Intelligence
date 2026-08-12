"""Respx-mocked tests for each adapter's `search()` method.

Live-network tests are still forbidden in CI. These tests intercept
HTTP calls via `respx` and assert both URL/param assembly and the
end-to-end `parse` path. They catch silent regressions in query
construction that fixture-only `parse` tests miss.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

respx = pytest.importorskip("respx")

from specint.records import License, SourceQuery  # noqa: E402
from specint.sources.archive_org import SEARCH_URL as ARCHIVE_URL  # noqa: E402
from specint.sources.archive_org import ArchiveOrgSource  # noqa: E402
from specint.sources.peertube import PeerTubeSource  # noqa: E402
from specint.sources.wikimedia import API_URL as WIKI_URL  # noqa: E402
from specint.sources.wikimedia import WikimediaCommonsSource  # noqa: E402
from specint.sources.youtube import SEARCH_URL as YT_SEARCH_URL  # noqa: E402
from specint.sources.youtube import VIDEOS_URL as YT_VIDEOS_URL  # noqa: E402
from specint.sources.youtube import YouTubeCCSource  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


@respx.mock
def test_wikimedia_search_hits_expected_endpoint_and_parses():
    payload = json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text())
    route = respx.get(WIKI_URL).mock(return_value=httpx.Response(200, json=payload))

    records = list(WikimediaCommonsSource().search(SourceQuery(terms=["pasta"], max_results=5)))
    assert route.called
    request = route.calls[0].request
    assert "gsrsearch=pasta+filetype%3Avideo" in str(request.url)
    assert "gsrnamespace=6" in str(request.url)
    assert records, "expected at least one record from fixture"
    assert all(r.source == "wikimedia" for r in records)


@respx.mock
def test_archive_org_search_hits_expected_endpoint_and_parses():
    payload = json.loads((FIXTURES / "archive_org/search_cooking.json").read_text())
    route = respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, json=payload))

    records = list(ArchiveOrgSource().search(SourceQuery(terms=["cooking"], max_results=10)))
    assert route.called
    request = route.calls[0].request
    assert "mediatype%3Amovies" in str(request.url)
    assert any(r.license.is_redistributable for r in records)


@respx.mock
def test_peertube_search_iterates_default_instances():
    payload = json.loads((FIXTURES / "peertube/search_cooking.json").read_text())
    routes = [
        respx.get("https://framatube.org/api/v1/search/videos").mock(
            return_value=httpx.Response(200, json=payload)
        ),
        respx.get("https://video.blender.org/api/v1/search/videos").mock(
            return_value=httpx.Response(200, json={"data": []})
        ),
        respx.get("https://tilvids.com/api/v1/search/videos").mock(
            return_value=httpx.Response(200, json={"data": []})
        ),
    ]
    records = list(PeerTubeSource().search(SourceQuery(terms=["cooking"], max_results=10)))
    assert all(r.called for r in routes)
    assert records and all(r.source == "peertube" for r in records)


@respx.mock
def test_peertube_search_swallows_instance_failures():
    payload = json.loads((FIXTURES / "peertube/search_cooking.json").read_text())
    respx.get("https://framatube.org/api/v1/search/videos").mock(return_value=httpx.Response(500))
    respx.get("https://video.blender.org/api/v1/search/videos").mock(
        return_value=httpx.Response(200, json=payload)
    )
    respx.get("https://tilvids.com/api/v1/search/videos").mock(
        side_effect=httpx.ConnectError("boom")
    )
    records = list(PeerTubeSource().search(SourceQuery(terms=["cooking"], max_results=10)))
    assert records, "should still get records from the surviving instance"


@respx.mock
def test_youtube_search_short_circuits_when_first_page_is_empty(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "fake-key")
    respx.get(YT_SEARCH_URL).mock(return_value=httpx.Response(200, json={"items": []}))
    records = list(YouTubeCCSource().search(SourceQuery(terms=["cooking"], max_results=5)))
    assert records == []


@respx.mock
def test_youtube_search_composes_two_calls_and_parses(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "fake-key")
    videos_payload = json.loads((FIXTURES / "youtube/videos_list.json").read_text())
    search_payload = {
        "items": [
            {"id": {"videoId": item["id"]}, "snippet": item["snippet"]}
            for item in videos_payload["items"]
        ]
    }
    search_route = respx.get(YT_SEARCH_URL).mock(
        return_value=httpx.Response(200, json=search_payload)
    )
    videos_route = respx.get(YT_VIDEOS_URL).mock(
        return_value=httpx.Response(200, json=videos_payload)
    )

    records = list(YouTubeCCSource().search(SourceQuery(terms=["cooking"], max_results=5)))
    assert search_route.called
    assert videos_route.called
    assert records, "expected creative-commons records"
    assert all(r.license is License.CC_BY for r in records)
    assert all(r.media_url is None for r in records)
