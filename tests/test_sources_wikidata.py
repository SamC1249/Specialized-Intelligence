from __future__ import annotations

import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.wikidata import WikidataSource


def test_wikidata_parses_bindings(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "wikidata/sparql_cooking.json").read_text())
    records = WikidataSource().parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    ids = {r.source_native_id for r in records}
    assert {"Q42000001", "Q42000002", "Q42000003"} <= ids

    lookup = {r.source_native_id: r for r in records}
    assert lookup["Q42000001"].license is License.CC_BY
    assert lookup["Q42000002"].license is License.CC_BY_SA
    assert lookup["Q42000003"].license is License.UNKNOWN
    assert lookup["Q42000003"].media_url is None
    assert lookup["Q42000001"].media_url is not None


def test_wikidata_build_sparql_contains_term():
    src = WikidataSource()
    q = src.build_sparql(SourceQuery(terms=["carbonara"], max_results=5))
    assert "carbonara" in q.lower()
    assert "LIMIT 5" in q


def test_wikidata_ignores_non_dict_input():
    assert WikidataSource().parse(None, SourceQuery(terms=[])) == []
    assert WikidataSource().parse([], SourceQuery(terms=[])) == []
