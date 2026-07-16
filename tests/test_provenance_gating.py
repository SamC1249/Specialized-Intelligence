"""Adversarial guard: every emitted VideoRecord must have real
provenance and must never leak a media URL when the license is not
redistributable. Fixture-driven so it stays offline.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIXTURES = Path(__file__).parent / "fixtures"


def _all_records() -> list:
    q = SourceQuery(terms=["cook"])
    records = []
    records.extend(
        WikimediaCommonsSource().parse(
            json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), q
        )
    )
    records.extend(
        WikimediaCommonsSource().parse(
            json.loads((FIXTURES / "wikimedia/multilingual.json").read_text()), q
        )
    )
    records.extend(
        ArchiveOrgSource().parse(
            json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), q
        )
    )
    records.extend(
        PeerTubeSource().parse(
            json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), q
        )
    )
    records.extend(
        PeerTubeSource().parse(
            json.loads((FIXTURES / "peertube/restricted_licence.json").read_text()), q
        )
    )
    records.extend(
        CommonCrawlRecipeSource().parse(
            {
                "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            q,
        )
    )
    records.extend(
        CommonCrawlRecipeSource().parse(
            {
                "html": (FIXTURES / "common_crawl/cc_licensed_recipe.html").read_text(),
                "url": "https://wikibooks-cookbook.example/cc-lasagna",
            },
            q,
        )
    )
    return records


def test_every_record_has_extractor_git_provenance():
    for r in _all_records():
        assert r.provenance.extractor, "extractor path missing"
        # get_extractor_git may return "dev" if no git and no env, but
        # it must never be empty and never be the literal placeholder
        # `"unset"` or `"None"`.
        assert r.provenance.extractor_git
        assert r.provenance.extractor_git not in {"unset", "None", "null"}


def test_no_media_url_when_license_is_restricted_or_unknown():
    for r in _all_records():
        if r.license is License.UNKNOWN or not r.license.is_redistributable:
            assert r.media_url is None, (
                f"record {r.id} leaks media_url {r.media_url} with license {r.license}"
            )
