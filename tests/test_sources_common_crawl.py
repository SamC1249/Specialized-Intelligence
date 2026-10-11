from specint.records import License, SourceQuery
from specint.sources.common_crawl import (
    CommonCrawlRecipeSource,
    classify_cc_url,
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
    assert r.license is License.UNKNOWN  # unlicensed fixture has no page-level signal
    assert r.media_url is None  # never expose media for unknown license
    assert len(r.recipe_steps) == 4
    assert any("al dente" in s for s in r.recipe_steps)


def test_classify_cc_url_covers_main_families():
    assert classify_cc_url("https://creativecommons.org/publicdomain/zero/1.0/") is License.CC0
    assert (
        classify_cc_url("https://creativecommons.org/publicdomain/mark/1.0/")
        is License.PUBLIC_DOMAIN
    )
    assert classify_cc_url("https://creativecommons.org/licenses/by/4.0/") is License.CC_BY
    assert classify_cc_url("https://creativecommons.org/licenses/by-sa/4.0/") is License.CC_BY_SA
    assert classify_cc_url("https://creativecommons.org/licenses/by-nc/4.0/") is License.RESTRICTED
    assert classify_cc_url("https://creativecommons.org/licenses/by-nd/4.0/") is License.RESTRICTED
    assert classify_cc_url("") is License.UNKNOWN


def test_cc_by_page_license_promotes_record(load_text):
    html = load_text("common_crawl/recipe_page_cc_by.html")
    records = parse_recipe_html(
        html,
        page_url="https://openrecipes.test/dal-tadka",
        query=SourceQuery(terms=["dal"]),
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.CC_BY
    assert r.license_url is not None and "by/4.0" in str(r.license_url)
    assert r.duration_s == 372.0  # PT6M12S


def test_cc_by_nc_page_license_blocks_redistribution(load_text):
    html = load_text("common_crawl/recipe_page_cc_by_nc.html")
    records = parse_recipe_html(
        html,
        page_url="https://blog.test/smash-burger",
        query=SourceQuery(terms=["burger"]),
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.RESTRICTED
    assert r.media_url is None


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
