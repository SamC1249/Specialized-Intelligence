"""Fuzz-lite: adapters must tolerate malformed upstream payloads.

Every `parse()` must degrade gracefully — no `KeyError`, no `TypeError`,
no `pydantic.ValidationError` — when upstream returns unexpected shapes.
Returned records (if any) must still validate as `VideoRecord`.
"""

from __future__ import annotations

import pytest

from specint.records import SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

QUERY = SourceQuery(terms=["cooking"], max_results=10)


def _run(source, raw):
    out = source.parse(raw, QUERY)
    assert isinstance(out, list)
    for r in out:
        assert isinstance(r, VideoRecord)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"query": None},
        {"query": {"pages": None}},
        {"query": {"pages": {"1": {"imageinfo": None}}}},
        {"query": {"pages": {"1": {"title": "File:x.webm", "imageinfo": [{"mime": "text/html"}]}}}},
        {"query": {"pages": {"1": {"title": "not a video", "imageinfo": [{"mime": "image/png"}]}}}},
        {"query": {"pages": {"1": {"title": None, "imageinfo": [{"mime": "video/webm"}]}}}},
    ],
)
def test_wikimedia_tolerates_malformed(raw):
    _run(WikimediaCommonsSource(), raw)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"response": None},
        {"response": {"docs": None}},
        {"response": {"docs": [{"identifier": None}]}},
        {"response": {"docs": [{"identifier": "abc", "runtime": ["not", "a", "string"]}]}},
        {
            "response": {
                "docs": [
                    {
                        "identifier": "abc",
                        "runtime": "12:34",
                        "subject": {"unexpected": "shape"},
                    }
                ]
            }
        },
    ],
)
def test_archive_org_tolerates_malformed(raw):
    _run(ArchiveOrgSource(), raw)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"data": None},
        {"data": [{}]},
        {"data": [{"licence": {"id": 99}, "uuid": "x"}]},
        {"data": [{"licence": {"id": 1}, "uuid": None}]},
        {
            "data": [
                {
                    "licence": {"id": 1},
                    "uuid": "abc",
                    "duration": "not-a-number",
                    "resolution": "not-a-dict",
                    "tags": None,
                }
            ]
        },
    ],
)
def test_peertube_tolerates_malformed(raw):
    _run(PeerTubeSource(), raw)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"html": None, "url": None},
        {
            "html": "<html><script type='application/ld+json'>not json</script></html>",
            "url": "https://x.test/",
        },
        {"html": "<html></html>", "url": "https://x.test/"},
        {
            "html": '<html><script type="application/ld+json">{"@type":"NotAVideo"}</script></html>',
            "url": "https://x.test/",
        },
    ],
)
def test_common_crawl_tolerates_malformed(raw):
    _run(CommonCrawlRecipeSource(), raw)
