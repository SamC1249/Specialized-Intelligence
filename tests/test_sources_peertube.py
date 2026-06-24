from specint.records import License, SourceQuery
from specint.sources.peertube import PeerTubeSource


def test_peertube_parse_filters_non_redistributable(load_json):
    raw = load_json("peertube/search_cooking.json")
    src = PeerTubeSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    titles = {r.title for r in records}
    assert "Open-Source Sourdough" in titles
    assert "Public-Domain Pancakes" in titles
    # NC video must be filtered.
    assert "Non-Commercial Stew" not in titles

    by_title = {r.title: r for r in records}
    sourdough = by_title["Open-Source Sourdough"]
    assert sourdough.license is License.CC_BY_SA
    assert sourdough.duration_s == 642
    assert sourdough.media_url is not None
    assert sourdough.author == "Open Bakers"

    pancakes = by_title["Public-Domain Pancakes"]
    assert pancakes.license is License.CC0
    assert pancakes.media_url is not None
