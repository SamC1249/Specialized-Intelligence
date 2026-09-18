from specint.records import License, SourceQuery
from specint.sources.youtube import YouTubeCreativeCommonsSource


def test_youtube_parse_only_cc_marked_videos_get_cc_by(load_json):
    raw = load_json("youtube/videos_cooking.json")
    src = YouTubeCreativeCommonsSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    assert {r.source for r in records} == {"youtube_cc"}
    by_id = {r.source_native_id: r for r in records}

    pesto = by_id["abc123XYZ01"]
    assert pesto.license is License.CC_BY
    assert str(pesto.url) == "https://www.youtube.com/watch?v=abc123XYZ01"
    assert pesto.duration_s == 8 * 60 + 12
    assert pesto.language == "en"
    assert pesto.author == "Open Kitchen Lab"

    suspicious = by_id["ghi789RST03"]
    assert suspicious.license is License.UNKNOWN


def test_youtube_no_media_url_regardless_of_license(load_json):
    raw = load_json("youtube/videos_cooking.json")
    src = YouTubeCreativeCommonsSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    for r in records:
        assert r.media_url is None


def test_youtube_parse_empty():
    src = YouTubeCreativeCommonsSource()
    assert src.parse({}, SourceQuery(terms=["cooking"])) == []
    assert src.parse({"items": []}, SourceQuery(terms=["cooking"])) == []
