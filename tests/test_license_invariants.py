"""License-safety invariants.

These tests enforce the constraint from AGENTS.md that we never
redistribute (or expose a direct `media_url` for) any record whose
license is not verifiably permissive. They apply to every checked-in
fixture — meaning if a *new* fixture ever slips in a RESTRICTED /
UNKNOWN record with a media_url, CI fails loudly.
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

_QUERY = SourceQuery(terms=["cooking", "recipe"], max_results=25)


def _parse_all(fixtures_dir: Path) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    records += WikimediaCommonsSource().parse(
        json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), _QUERY
    )
    records += ArchiveOrgSource().parse(
        json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), _QUERY
    )
    records += PeerTubeSource().parse(
        json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), _QUERY
    )
    records += CommonCrawlRecipeSource().parse(
        {
            "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
            "url": "https://example.test/recipes/garlic-butter-pasta",
        },
        _QUERY,
    )
    return records


def test_no_restricted_or_unknown_media_url(fixtures_dir: Path):
    for rec in _parse_all(fixtures_dir):
        if not rec.license.is_redistributable:
            assert rec.media_url is None, (
                f"license-invariant violated: {rec.source} record {rec.id} carries "
                f"license={rec.license.value} but exposes media_url={rec.media_url!r}"
            )


def test_all_records_carry_provenance(fixtures_dir: Path):
    for rec in _parse_all(fixtures_dir):
        assert rec.provenance is not None
        assert rec.provenance.extractor
        assert rec.id.startswith(f"{rec.source}:")


@pytest.mark.parametrize(
    "license,is_redistributable",
    [
        (License.CC0, True),
        (License.CC_BY, True),
        (License.CC_BY_SA, True),
        (License.PUBLIC_DOMAIN, True),
        (License.OTHER_FREE, True),
        (License.UNKNOWN, False),
        (License.RESTRICTED, False),
    ],
)
def test_license_redistributable_flag(license: License, is_redistributable: bool):
    assert license.is_redistributable is is_redistributable
