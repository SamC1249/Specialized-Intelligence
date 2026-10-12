"""Unit test for the YouTube CC-only adapter against a checked-in fixture.

Covers two invariants we care about:
  - Records whose per-video `status.license` is not `creativeCommon` must
    fall through to `License.UNKNOWN` even if they were returned by the
    `videoLicense=creativeCommon` search filter.
  - `media_url` must always be `None`; this adapter is URL + metadata
    only per `AGENTS.md`.
"""

from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.youtube_cc import YouTubeCCSource


def test_parse_youtube_cc_fixture(load_json):
    raw = load_json("youtube_cc/search_cooking.json")
    query = SourceQuery(terms=["cooking", "recipe"])
    records = YouTubeCCSource().parse(raw, query)

    assert len(records) == 3

    by_id = {r.source_native_id: r for r in records}

    good = by_id["ccVideoAAAA"]
    assert good.license is License.CC_BY
    assert good.media_url is None
    assert str(good.url) == "https://www.youtube.com/watch?v=ccVideoAAAA"
    assert good.duration_s == 6 * 60 + 12
    assert good.height == 720
    assert good.author == "OpenKitchen"
    assert good.language == "en"

    bad = by_id["ytStandardCCC"]
    assert bad.license is License.UNKNOWN
    assert bad.media_url is None
    assert bad.license_url is None

    for record in records:
        assert record.media_url is None
        assert record.source == "youtube_cc"
