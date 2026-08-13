from specint.records import License, SourceQuery
from specint.sources.wikimedia import WikimediaCommonsSource


def test_wikimedia_parse_filters_non_video_and_classifies_license(load_json):
    raw = load_json("wikimedia/search_pasta.json")
    src = WikimediaCommonsSource()
    records = src.parse(raw, SourceQuery(terms=["pasta"], max_results=10))
    assert {r.source for r in records} == {"wikimedia"}
    titles = {r.title for r in records}
    # Cleaned titles strip the "File:" prefix and the video extension.
    assert "Cooking pasta carbonara" in titles
    assert "Knife skills demo" in titles
    # The image must be filtered out.
    assert not any(t.lower().endswith(".jpg") for t in titles)
    assert not any("some_image" in t.lower() for t in titles)

    by_title = {r.title: r for r in records}
    pasta = by_title["Cooking pasta carbonara"]
    assert pasta.license is License.CC_BY_SA
    assert pasta.duration_s == 312.4
    assert pasta.height == 1080
    assert pasta.media_url is not None
    assert pasta.author == "Jane Cook"

    knife = by_title["Knife skills demo"]
    assert knife.license is License.CC0
    assert knife.media_url is not None


def test_wikimedia_parse_handles_empty():
    src = WikimediaCommonsSource()
    assert src.parse({}, SourceQuery(terms=["x"])) == []
    assert src.parse({"query": {"pages": {}}}, SourceQuery(terms=["x"])) == []


def test_wikimedia_parse_captures_multilingual_titles(load_json):
    raw = load_json("wikimedia/search_pasta.json")
    src = WikimediaCommonsSource()
    records = src.parse(raw, SourceQuery(terms=["cocinar"], max_results=10))
    titles = {r.title for r in records}
    assert "Cocinar paella valenciana" in titles
