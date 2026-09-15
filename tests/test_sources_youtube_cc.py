import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCCSource


def test_parse_youtube_cc_fixture(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/search_cooking.json").read_text())
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"], max_results=25))
    assert len(records) == 3
    r = records[0]
    assert r.source == "youtube_cc"
    assert r.id == "youtube_cc:abc123EXAMPLE"
    assert str(r.url) == "https://www.youtube.com/watch?v=abc123EXAMPLE"
    assert r.media_url is None  # AGENTS.md: URL + metadata only.
    assert r.license == License.CC_BY
    assert r.duration_s == 4 * 60 + 30
    assert r.author == "Open Kitchen"
    assert "cooking" in r.keywords


def test_parse_ignores_items_without_video_id():
    raw = {"items": [{"id": {"kind": "youtube#channel"}, "snippet": {"title": "chan"}}]}
    assert YouTubeCCSource().parse(raw, SourceQuery(terms=["x"])) == []


def test_search_no_op_without_api_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    src = YouTubeCCSource()
    assert list(src.search(SourceQuery(terms=["cooking"]))) == []
