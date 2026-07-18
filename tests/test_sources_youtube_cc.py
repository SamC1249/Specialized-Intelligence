import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCCSource


def test_youtube_cc_parses_only_cc_licensed(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/search_cooking.json").read_text())
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    ids = {r.source_native_id for r in records}
    assert ids == {"abcCC1234", "defCC5678"}


def test_youtube_cc_never_populates_media_url(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/search_cooking.json").read_text())
    records = YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    assert records, "expected at least one CC record"
    for r in records:
        assert r.media_url is None
        assert r.license == License.CC_BY
        assert str(r.url).startswith("https://www.youtube.com/watch?v=")


def test_youtube_cc_parses_iso_duration_and_dimensions(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "youtube_cc/search_cooking.json").read_text())
    records = {
        r.source_native_id: r for r in YouTubeCCSource().parse(raw, SourceQuery(terms=["cooking"]))
    }
    assert records["abcCC1234"].duration_s == 312.0
    assert records["defCC5678"].duration_s == 22 * 60
    assert records["abcCC1234"].height == 1080


def test_youtube_cc_search_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("SPECINT_YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    assert list(YouTubeCCSource().search(SourceQuery(terms=["x"]))) == []
