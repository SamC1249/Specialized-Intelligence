import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCCSource


def test_youtube_cc_parses_only_creativecommon(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/videos_cooking.json").read_text())
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    ids = {r.source_native_id for r in records}
    assert "abcDEF12345" in ids
    assert "cc0RECIPE001" in ids
    assert "zyxwVUT98765" not in ids
    for r in records:
        assert r.license is License.CC_BY
        assert r.url.host == "www.youtube.com"
        assert r.media_url is None


def test_youtube_cc_maps_duration_and_definition(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/videos_cooking.json").read_text())
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    by_id = {r.source_native_id: r for r in records}
    assert by_id["abcDEF12345"].duration_s == 12 * 60 + 34
    assert by_id["abcDEF12345"].height == 720
    assert by_id["cc0RECIPE001"].height == 360
    assert by_id["cc0RECIPE001"].language == "it"


def test_youtube_cc_parse_ignores_non_dict():
    assert YouTubeCCSource().parse([], SourceQuery(terms=["x"])) == []
    assert YouTubeCCSource().parse({"items": [None, 42]}, SourceQuery(terms=["x"])) == []
