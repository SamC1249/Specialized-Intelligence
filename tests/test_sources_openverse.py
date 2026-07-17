"""Offline unit test for the Openverse adapter."""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.openverse import OpenverseSource


def test_openverse_parse_drops_non_redistributable(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "openverse/search_cooking.json").read_text())
    records = OpenverseSource().parse(raw, SourceQuery(terms=["cooking"]))

    ids = {r.source_native_id for r in records}
    assert "ov-0003" not in ids  # BY-NC-ND must be filtered
    assert "ov-0001" in ids and "ov-0002" in ids


def test_openverse_parse_licenses_and_provenance(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "openverse/search_cooking.json").read_text())
    query = SourceQuery(terms=["cooking", "recipe"], max_results=10)
    records = OpenverseSource().parse(raw, query)

    for r in records:
        assert r.source == "openverse"
        assert r.license.is_redistributable
        assert r.provenance.extractor.endswith("openverse")
        assert "cooking" in r.provenance.query

    ov1 = next(r for r in records if r.source_native_id == "ov-0001")
    assert ov1.license is License.CC_BY_SA
    assert ov1.height == 1080
    assert ov1.language == "en"
    assert ov1.duration_s == 420.0

    ov2 = next(r for r in records if r.source_native_id == "ov-0002")
    assert ov2.license is License.CC_BY
    assert ov2.language == "es"


def test_openverse_parse_handles_empty_or_bad_input():
    src = OpenverseSource()
    assert src.parse(None, SourceQuery(terms=[])) == []
    assert src.parse({}, SourceQuery(terms=[])) == []
    assert src.parse({"results": []}, SourceQuery(terms=[])) == []
