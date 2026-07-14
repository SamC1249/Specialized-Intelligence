"""Common Crawl license-lift tests (H4)."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from specint.records import License, SourceQuery
from specint.sources.common_crawl import CommonCrawlRecipeSource, extract_page_license


def test_unlicensed_page_stays_unknown(fixtures_dir: Path):
    html = (fixtures_dir / "common_crawl/recipe_page.html").read_text()
    query = SourceQuery(terms=["cooking"])
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/garlic-butter-pasta"}, query
    )
    assert records
    assert all(r.license is License.UNKNOWN for r in records)


def test_cc_licensed_page_lifts_to_cc_by(fixtures_dir: Path):
    html = (fixtures_dir / "common_crawl/cc_licensed_recipe.html").read_text()
    soup = BeautifulSoup(html, "lxml")
    license_enum, url = extract_page_license(soup)
    assert license_enum is License.CC_BY
    assert url is not None and "creativecommons.org" in url

    query = SourceQuery(terms=["cooking"])
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/braised-short-ribs"}, query
    )
    assert records
    assert all(r.license is License.CC_BY for r in records)
    assert all(str(r.license_url).startswith("https://creativecommons.org/") for r in records)


def test_meta_only_license_does_not_lift():
    html = (
        "<html><head>"
        '<meta name="license" content="https://creativecommons.org/licenses/by/4.0">'
        "</head><body></body></html>"
    )
    soup = BeautifulSoup(html, "lxml")
    license_enum, url = extract_page_license(soup)
    assert license_enum is License.UNKNOWN
    assert url is None
