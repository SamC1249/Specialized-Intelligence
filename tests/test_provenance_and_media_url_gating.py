"""Adversarial invariants over every fixture-parsed record.

Two invariants any adapter must uphold:

1.  **Provenance is mandatory.** Every emitted `VideoRecord` carries a
    non-empty `provenance.extractor` and a non-empty
    `provenance.query`. AGENTS.md rule 2.

2.  **No `media_url` leaks for non-redistributable licenses.** A record
    whose `license.is_redistributable` is False must have
    `media_url is None`. A regression here would put a corpus at legal
    risk even if downstream code trusts the license field.

These tests walk every fixture we ship and every registered adapter's
`parse()`, so a new adapter is automatically covered as soon as it
ships a fixture named `<slug>/*.json` (or, for common_crawl,
`<slug>/*.html`).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.records import License, SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _all_fixture_records() -> list[tuple[str, VideoRecord]]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    out: list[tuple[str, VideoRecord]] = []
    for path in sorted((FIXTURES / "wikimedia").glob("*.json")):
        for r in WikimediaCommonsSource().parse(json.loads(path.read_text()), query):
            out.append((f"wikimedia:{path.name}", r))
    for path in sorted((FIXTURES / "archive_org").glob("*.json")):
        for r in ArchiveOrgSource().parse(json.loads(path.read_text()), query):
            out.append((f"archive_org:{path.name}", r))
    for path in sorted((FIXTURES / "peertube").glob("*.json")):
        for r in PeerTubeSource().parse(json.loads(path.read_text()), query):
            out.append((f"peertube:{path.name}", r))
    for path in sorted((FIXTURES / "common_crawl").glob("*.html")):
        payload = {"html": path.read_text(), "url": f"https://example.test/{path.stem}"}
        for r in CommonCrawlRecipeSource().parse(payload, query):
            out.append((f"common_crawl:{path.name}", r))
    return out


ALL_RECORDS = _all_fixture_records()


def test_fixture_universe_is_non_empty() -> None:
    assert ALL_RECORDS, "no fixture-parsed records found — did the fixture layout change?"


@pytest.mark.parametrize("label, record", ALL_RECORDS, ids=[label for label, _ in ALL_RECORDS])
def test_provenance_is_populated(label: str, record: VideoRecord) -> None:
    assert record.provenance is not None, f"{label}: missing provenance"
    assert record.provenance.extractor, f"{label}: empty provenance.extractor"
    assert record.provenance.query, f"{label}: empty provenance.query"
    assert record.provenance.fetched_at is not None, f"{label}: missing fetched_at"


@pytest.mark.parametrize("label, record", ALL_RECORDS, ids=[label for label, _ in ALL_RECORDS])
def test_media_url_is_gated_by_license(label: str, record: VideoRecord) -> None:
    if record.license is License.UNKNOWN or record.license is License.RESTRICTED:
        assert record.media_url is None, (
            f"{label}: media_url leaked for non-redistributable license {record.license.value}"
        )


@pytest.mark.parametrize("label, record", ALL_RECORDS, ids=[label for label, _ in ALL_RECORDS])
def test_id_uses_source_prefix(label: str, record: VideoRecord) -> None:
    assert record.id.startswith(f"{record.source}:"), (
        f"{label}: record.id={record.id!r} does not begin with source slug {record.source!r}"
    )
