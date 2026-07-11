from specint.records import License, SourceQuery
from specint.sources.youtube import YouTubeCCSource, _parse_iso_duration


def test_youtube_iso_duration_parses():
    assert _parse_iso_duration("PT12M30S") == 750.0
    assert _parse_iso_duration("PT1H2M3S") == 3723.0
    assert _parse_iso_duration(None) is None
    assert _parse_iso_duration("bad") is None


def test_youtube_parse_marks_only_creativecommon_as_cc(load_json):
    raw = load_json("youtube/videos_cooking.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    by_id = {r.source_native_id: r for r in records}
    assert set(by_id) == {"yt_cook_001", "yt_cook_002", "yt_cook_003"}
    assert by_id["yt_cook_001"].license is License.CC_BY
    assert by_id["yt_cook_002"].license is License.RESTRICTED
    assert by_id["yt_cook_003"].license is License.CC_BY


def test_youtube_never_emits_media_url(load_json):
    raw = load_json("youtube/videos_cooking.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    for r in records:
        assert r.media_url is None, f"{r.id} exposed a media_url; YouTube forbids that."


def test_youtube_hd_maps_to_720p_when_no_explicit_height(load_json):
    raw = load_json("youtube/videos_cooking.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    r = next(r for r in records if r.source_native_id == "yt_cook_001")
    assert r.height == 720
    assert r.duration_s == 750.0


def test_youtube_parse_handles_empty_and_malformed():
    src = YouTubeCCSource()
    q = SourceQuery(terms=["x"])
    assert src.parse({}, q) == []
    assert src.parse({"items": []}, q) == []
    assert src.parse("not a dict", q) == []


def test_youtube_url_landing_page_only(load_json):
    raw = load_json("youtube/videos_cooking.json")
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    r = next(r for r in records if r.source_native_id == "yt_cook_001")
    assert str(r.url) == "https://www.youtube.com/watch?v=yt_cook_001"
