"""Adversarial fixtures for every source adapter.

The goal is not to *fix* every hostile upstream, but to guarantee we
never *crash* on one and never *upgrade* a hostile input past its
truthful license class. Every case here corresponds to a real class of
upstream bug we have already seen in the wild.

See `docs/plan-2026-07-12.md` §3 "Adversarial parser fixtures."
"""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

_QUERY = SourceQuery(terms=["cooking"], max_results=10)


def test_wikimedia_parse_handles_junk_payloads() -> None:
    src = WikimediaCommonsSource()
    assert src.parse(None, _QUERY) == []  # type: ignore[arg-type]
    assert src.parse([], _QUERY) == []  # type: ignore[arg-type]
    assert src.parse({"query": None}, _QUERY) == []
    assert src.parse({"query": {"pages": None}}, _QUERY) == []


def test_wikimedia_license_label_and_url_disagree_downgrades_to_restricted() -> None:
    src = WikimediaCommonsSource()
    raw = {
        "query": {
            "pages": {
                "1": {
                    "pageid": 1,
                    "title": "File:Sneaky_recipe.webm",
                    "imageinfo": [
                        {
                            "mime": "video/webm",
                            "url": "https://example.org/x.webm",
                            "descriptionurl": "https://example.org/x",
                            "duration": 300,
                            "width": 1280,
                            "height": 720,
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY 4.0"},
                                "LicenseUrl": {
                                    "value": "https://creativecommons.org/licenses/by-nc/4.0/"
                                },
                            },
                        }
                    ],
                }
            }
        }
    }
    records = src.parse(raw, _QUERY)
    assert len(records) == 1
    assert records[0].license is License.RESTRICTED
    assert records[0].media_url is None


def test_archive_org_parse_handles_junk() -> None:
    src = ArchiveOrgSource()
    assert src.parse(None, _QUERY) == []  # type: ignore[arg-type]
    assert src.parse({"response": None}, _QUERY) == []
    assert src.parse({"response": {"docs": None}}, _QUERY) == []


def test_archive_org_rights_field_carries_nc_signal() -> None:
    src = ArchiveOrgSource()
    raw = {
        "response": {
            "docs": [
                {
                    "identifier": "Foo",
                    "title": "Foo",
                    "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
                    "rights": "Attribution-NonCommercial 4.0 International",
                    "runtime": "0:05:00",
                }
            ]
        }
    }
    records = src.parse(raw, _QUERY)
    assert len(records) == 1
    assert records[0].license is License.RESTRICTED
    assert records[0].media_url is None


def test_archive_org_bad_runtime_does_not_crash() -> None:
    src = ArchiveOrgSource()
    raw = {
        "response": {
            "docs": [
                {"identifier": "A", "title": "A", "runtime": "not-a-duration"},
                {"identifier": "B", "title": "B", "runtime": ["not-a-string"]},
                {"identifier": "C", "title": "C", "runtime": -1},
            ]
        }
    }
    records = src.parse(raw, _QUERY)
    assert {r.source_native_id for r in records} == {"A", "B", "C"}


def test_peertube_parse_handles_junk() -> None:
    src = PeerTubeSource()
    assert src.parse(None, _QUERY) == []  # type: ignore[arg-type]
    assert src.parse({"data": None}, _QUERY) == []


def test_peertube_restricted_label_wins_over_permissive_id() -> None:
    """PeerTube licence id=1 (CC-BY) with a label saying 'Attribution-
    NonCommercial 4.0' must drop the record; the label is more specific
    than the numeric id."""
    src = PeerTubeSource()
    raw = {
        "data": [
            {
                "uuid": "abc",
                "name": "Sneaky Video",
                "licence": {
                    "id": 1,
                    "label": "Attribution-NonCommercial 4.0 International",
                },
                "account": {"host": "framatube.org", "displayName": "Uploader"},
                "duration": 100,
                "files": [{"fileUrl": "https://framatube.org/a"}],
            }
        ]
    }
    records = src.parse(raw, _QUERY)
    assert records == []


def test_common_crawl_parse_handles_junk() -> None:
    src = CommonCrawlRecipeSource()
    assert src.parse(None, _QUERY) == []  # type: ignore[arg-type]
    assert src.parse({"html": 42, "url": "x"}, _QUERY) == []
    assert src.parse({"html": "<html/>", "url": 42}, _QUERY) == []


def test_common_crawl_malformed_jsonld_does_not_raise() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">{not: valid json}</script>
      <script type="application/ld+json">null</script>
      <script type="application/ld+json">[]</script>
      <link rel="license" href="https://creativecommons.org/licenses/by/4.0/" />
    </head><body></body></html>
    """
    src = CommonCrawlRecipeSource()
    records = src.parse({"html": html, "url": "https://example.test/"}, _QUERY)
    assert records == []


def test_common_crawl_page_level_license_downgrades_on_nc() -> None:
    html = """
    <html><head>
      <link rel="license" href="https://creativecommons.org/licenses/by-nc/4.0/" />
      <script type="application/ld+json">
        {"@type": "VideoObject", "name": "Sneaky", "contentUrl": "https://x.example/v.mp4"}
      </script>
    </head><body></body></html>
    """
    src = CommonCrawlRecipeSource()
    records = src.parse({"html": html, "url": "https://example.test/"}, _QUERY)
    assert len(records) == 1
    assert records[0].license is License.RESTRICTED
