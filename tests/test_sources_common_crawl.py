from specint.records import License, SourceQuery
from specint.sources.common_crawl import (
    CommonCrawlRecipeSource,
    infer_license_from_url,
    parse_iso8601_duration,
    parse_recipe_html,
)


def test_iso8601_duration():
    assert parse_iso8601_duration("PT4M30S") == 270.0
    assert parse_iso8601_duration("PT1H") == 3600.0
    assert parse_iso8601_duration(None) is None
    assert parse_iso8601_duration("not a duration") is None


def test_common_crawl_parse_recipe_html(load_text):
    html = load_text("common_crawl/recipe_page.html")
    records = parse_recipe_html(
        html,
        page_url="https://example.test/recipes/garlic-butter-pasta",
        query=SourceQuery(terms=["pasta"], max_results=10),
    )
    assert len(records) == 1
    r = records[0]
    assert r.source == "common_crawl"
    assert r.duration_s == 270.0
    assert r.height == 1080
    assert r.author == "Sam Cook"
    assert r.license is License.UNKNOWN  # we never auto-trust embedded license
    assert r.media_url is None  # never expose media for unknown license
    assert len(r.recipe_steps) == 4
    assert any("al dente" in s for s in r.recipe_steps)


def test_infer_license_from_url_maps_cc_canonical_urls():
    assert infer_license_from_url("https://creativecommons.org/licenses/by/4.0/") is License.CC_BY
    assert (
        infer_license_from_url("https://creativecommons.org/licenses/by-sa/4.0/")
        is License.CC_BY_SA
    )
    assert (
        infer_license_from_url("https://creativecommons.org/publicdomain/zero/1.0/") is License.CC0
    )
    assert (
        infer_license_from_url("https://creativecommons.org/licenses/by-nc/4.0/")
        is License.RESTRICTED
    )
    assert (
        infer_license_from_url("https://creativecommons.org/licenses/by-nd/4.0/")
        is License.RESTRICTED
    )
    assert infer_license_from_url("https://example.com/terms") is License.UNKNOWN
    assert infer_license_from_url(None) is License.UNKNOWN
    assert infer_license_from_url("") is License.UNKNOWN


def test_parse_recipe_html_upgrades_license_from_page_link_tag():
    html = """<!doctype html>
    <html><head>
      <link rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">
      <script type="application/ld+json">
      {"@type": "VideoObject", "@id": "https://x.test/v", "name": "Recipe demo",
       "duration": "PT2M", "contentUrl": "https://x.test/v.mp4"}
      </script>
    </head><body></body></html>"""
    records = parse_recipe_html(
        html,
        page_url="https://x.test/",
        query=SourceQuery(terms=["cooking"]),
    )
    assert len(records) == 1
    assert records[0].license is License.CC_BY_SA
    assert records[0].license_url is not None and "creativecommons.org/licenses/by-sa" in str(
        records[0].license_url
    )


def test_parse_recipe_html_upgrades_license_from_jsonld_field():
    html = """<!doctype html>
    <html><head>
      <script type="application/ld+json">
      {"@type": "VideoObject", "@id": "https://x.test/v", "name": "Recipe demo",
       "duration": "PT2M", "license": "https://creativecommons.org/publicdomain/zero/1.0/"}
      </script>
    </head><body></body></html>"""
    records = parse_recipe_html(
        html,
        page_url="https://x.test/",
        query=SourceQuery(terms=["cooking"]),
    )
    assert len(records) == 1
    assert records[0].license is License.CC0


def test_common_crawl_source_parse_dispatch(load_text):
    src = CommonCrawlRecipeSource()
    raw = {"html": load_text("common_crawl/recipe_page.html"), "url": "https://example.test/r"}
    records = src.parse(raw, SourceQuery(terms=["pasta"]))
    assert len(records) == 1
    assert (
        src.parse(
            {"html": "<html></html>", "url": "https://example.test/r"}, SourceQuery(terms=["pasta"])
        )
        == []
    )
    assert src.parse({}, SourceQuery(terms=["pasta"])) == []
