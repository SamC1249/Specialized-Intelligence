"""Provenance completeness — every fixture record must carry raw_sha256.

If the run is inside a git checkout, `extractor_git` must not be `"dev"`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.gitmeta import short_sha
from specint.records import SourceQuery, make_provenance
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "source_cls, raw_payload_factory",
    [
        (
            WikimediaCommonsSource,
            lambda: json.loads((FIX / "wikimedia/search_pasta.json").read_text()),
        ),
        (
            ArchiveOrgSource,
            lambda: json.loads((FIX / "archive_org/search_cooking.json").read_text()),
        ),
        (
            PeerTubeSource,
            lambda: json.loads((FIX / "peertube/search_cooking.json").read_text()),
        ),
        (
            CommonCrawlRecipeSource,
            lambda: {
                "html": (FIX / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
        ),
    ],
)
def test_all_records_have_raw_sha256(source_cls, raw_payload_factory):
    query = SourceQuery(terms=["cooking"], max_results=25)
    records = source_cls().parse(raw_payload_factory(), query)
    assert records, f"{source_cls.__name__} produced no records from fixture"
    for r in records:
        assert r.provenance.raw_sha256, r
        assert len(r.provenance.raw_sha256) == 64
        assert r.provenance.extractor.startswith("specint.sources")


def test_git_sha_is_real_when_inside_git_checkout():
    sha = short_sha()
    if sha == "unknown":
        pytest.skip("not inside a git checkout")
    assert sha != "dev"
    assert len(sha) == 7


def test_make_provenance_defaults_are_populated():
    prov = make_provenance("specint.sources.test", "q=1", raw={"a": 1})
    assert prov.raw_sha256
    assert prov.extractor_git != "dev"
    assert prov.query == "q=1"
    assert prov.rights is None
