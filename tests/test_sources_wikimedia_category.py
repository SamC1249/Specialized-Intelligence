from specint.records import License, SourceQuery
from specint.sources.wikimedia_category import WikimediaCommonsCategorySource


def test_wikimedia_category_parse_reuses_search_parser(load_json):
    raw = load_json("wikimedia_category/category_cooking.json")
    src = WikimediaCommonsCategorySource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=25))

    assert {r.source for r in records} == {"wikimedia_category"}
    assert all(r.id.startswith("wikimedia_category:") for r in records)

    by_title = {r.title: r for r in records}
    bread = by_title["File:Baking bread whole grain.webm"]
    assert bread.license is License.CC_BY
    assert bread.media_url is not None
    assert bread.duration_s == 480.0

    omelette = by_title["File:French omelette technique.ogv"]
    assert omelette.license is License.CC0
    assert omelette.media_url is not None

    restricted = by_title["File:Restricted_cooking_footage.mp4"]
    assert restricted.license is License.RESTRICTED
    assert restricted.media_url is None


def test_wikimedia_category_parse_handles_empty():
    src = WikimediaCommonsCategorySource()
    assert src.parse({}, SourceQuery(terms=["cooking"])) == []
