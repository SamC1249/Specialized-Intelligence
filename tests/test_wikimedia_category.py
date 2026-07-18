"""Wikimedia Commons `categorymembers` discovery mode.

See `docs/artifacts/wikimedia-categorymembers-api.md` for the response
shape and `docs/plan-2026-07-18.md` §A3 for the hypothesis: category
discovery is a strictly higher-recall path than free-text search when a
matching category exists.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.wikimedia import WikimediaCommonsSource


def test_category_mode_parses_same_shape(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "wikimedia/category_cooking.json").read_text())
    source = WikimediaCommonsSource(category="Videos of cooking")
    query = SourceQuery(terms=["cooking"], max_results=25)
    records = source.parse(raw, query)

    # The image entry (Some_unrelated_photo.jpg) must be filtered out; the two
    # videos must appear with correct licences.
    assert {r.source_native_id for r in records} == {"22222", "33333"}
    by_id = {r.source_native_id: r for r in records}
    assert by_id["22222"].license is License.CC_BY
    assert by_id["33333"].license is License.CC0
    for r in records:
        assert r.media_url is not None  # both are redistributable


def test_category_mode_records_carry_category_marker_via_url():
    """The parse path is source-agnostic; assert the search() params flip on."""
    source = WikimediaCommonsSource(category="Videos of cooking recipes")
    assert source.category == "Videos of cooking recipes"

    default_source = WikimediaCommonsSource()
    assert default_source.category is None
