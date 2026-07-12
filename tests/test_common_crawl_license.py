from __future__ import annotations

from bs4 import BeautifulSoup

from specint.records import License, SourceQuery
from specint.sources.common_crawl import extract_page_license, parse_recipe_html


def test_extract_license_from_link_rel_license():
    html = """
    <html><head>
      <link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
    </head><body></body></html>
    """
    lic, url = extract_page_license(BeautifulSoup(html, "lxml"))
    assert lic is License.CC_BY
    assert "creativecommons.org/licenses/by/4.0" in url


def test_extract_license_from_dcterms_meta():
    html = """
    <html><head>
      <meta name="dcterms.rights" content="https://creativecommons.org/publicdomain/zero/1.0/">
    </head></html>
    """
    lic, _ = extract_page_license(BeautifulSoup(html, "lxml"))
    assert lic is License.CC0


def test_extract_license_from_body_anchor():
    html = """
    <html><head></head><body>
      <p>Released under
      <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC-BY-SA 4.0</a>.
      </p>
    </body></html>
    """
    lic, _ = extract_page_license(BeautifulSoup(html, "lxml"))
    assert lic is License.CC_BY_SA


def test_extract_license_flags_non_commercial_as_restricted():
    html = """
    <html><head>
      <link rel="license" href="https://creativecommons.org/licenses/by-nc/4.0/">
    </head></html>
    """
    lic, _ = extract_page_license(BeautifulSoup(html, "lxml"))
    assert lic is License.RESTRICTED


def test_extract_license_unknown_when_no_signal():
    html = "<html><body><h1>No license here</h1></body></html>"
    lic, url = extract_page_license(BeautifulSoup(html, "lxml"))
    assert lic is License.UNKNOWN
    assert url is None


def test_parse_recipe_page_ccby_marks_records_ccby(load_text):
    html = load_text("common_crawl/recipe_page_ccby.html")
    records = parse_recipe_html(
        html,
        page_url="https://example.test/recipes/sourdough-loaf",
        query=SourceQuery(terms=["sourdough"]),
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.CC_BY
    assert r.license_url is not None
    assert "by/4.0" in str(r.license_url)
    assert r.media_url is None


def test_parse_recipe_page_bync_marks_records_restricted(load_text):
    html = load_text("common_crawl/recipe_page_bync.html")
    records = parse_recipe_html(
        html,
        page_url="https://example.test/recipes/mousse",
        query=SourceQuery(terms=["mousse"]),
    )
    assert len(records) == 1
    assert records[0].license is License.RESTRICTED
    assert records[0].media_url is None
