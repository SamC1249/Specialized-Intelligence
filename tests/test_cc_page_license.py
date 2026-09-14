"""Common-Crawl page-license extraction — the JSON-LD lies risk."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from specint.records import License, SourceQuery
from specint.sources.common_crawl import CommonCrawlRecipeSource, extract_page_license


def _fixtures() -> Path:
    return Path(__file__).parent / "fixtures"


def test_page_license_extracted_from_link_rel() -> None:
    html = (_fixtures() / "common_crawl/recipe_page.html").read_text()
    soup = BeautifulSoup(html, "lxml")
    license_enum, url = extract_page_license(soup)
    assert license_enum is License.CC_BY_SA
    assert url and "by-sa" in url


def test_lying_jsonld_is_overridden_by_page_license() -> None:
    html = (_fixtures() / "common_crawl/recipe_page_lying.html").read_text()
    query = SourceQuery(terms=["ragu"], max_results=1)
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/secret-ragu"},
        query,
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.RESTRICTED, (
        "Page rel=license says All Rights Reserved; JSON-LD lies about CC-BY. "
        "Rule of least privilege must classify this as RESTRICTED."
    )
    assert r.media_url is None


def test_honest_cc_by_sa_page_yields_clean_record() -> None:
    html = (_fixtures() / "common_crawl/recipe_page.html").read_text()
    query = SourceQuery(terms=["pasta"], max_results=1)
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/garlic-butter-pasta"},
        query,
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.CC_BY_SA
    assert r.license.is_redistributable
    assert r.license_url is not None
