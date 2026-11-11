"""License-floor regression: the fixture corpus must exercise both the
`is_redistributable=True` path and the `License.UNKNOWN` path.

This is intentionally an **aggregate-level** floor today because current
fixtures are tiny (8 records) and several per-source fixtures contain
only one record. The plan in `docs/plan-2026-11-11.md` tightens this to
a per-source floor once we add adversarial fixtures (laundered license,
disagreeing license strings, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _load_all(fixtures_dir: Path) -> list:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    records: list = []
    records.extend(
        WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        )
    )
    records.extend(
        ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        )
    )
    records.extend(
        PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        )
    )
    records.extend(
        CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        )
    )
    return records


def test_fixture_corpus_has_at_least_one_redistributable(fixtures_dir: Path) -> None:
    records = _load_all(fixtures_dir)
    redistributable = [r for r in records if r.license.is_redistributable]
    assert redistributable, (
        "fixture corpus has zero redistributable records; license classification is probably "
        "broken or fixtures have drifted"
    )


def test_fixture_corpus_has_at_least_one_unknown(fixtures_dir: Path) -> None:
    records = _load_all(fixtures_dir)
    unknown = [r for r in records if r.license is License.UNKNOWN]
    assert unknown, (
        "fixture corpus has zero UNKNOWN-license records; the `License.UNKNOWN` fallback path "
        "is no longer exercised. Add a fixture with ambiguous license metadata or confirm the "
        "classifier should default to UNKNOWN."
    )


def test_every_record_has_provenance(fixtures_dir: Path) -> None:
    records = _load_all(fixtures_dir)
    for r in records:
        assert r.provenance is not None, f"record {r.id} missing provenance"
        assert r.provenance.extractor, f"record {r.id} has empty extractor"
