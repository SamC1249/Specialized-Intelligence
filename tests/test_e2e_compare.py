"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from specint.compare import load_fixture_records, run_comparison
from specint.records import License, Provenance, SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)

    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {"wikimedia", "archive_org", "peertube", "common_crawl", "__total__"}

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    # License-clean count must be monotonically <= n_records.
    for row in rows:
        assert row.n_license_clean <= row.n_records

    # Every row must expose the new dedup counter.
    for row in rows:
        assert row.n_unique_after_dedup <= row.n_records

    # Persist a sample report to validate the JSON serialisation contract.
    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == 5


def test_load_fixture_records_matches_manual_loading(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_fixture_records(query, fixtures_dir=fixtures_dir)
    assert set(by_source) == {"wikimedia", "archive_org", "peertube", "common_crawl"}
    assert sum(len(v) for v in by_source.values()) > 0


def test_cross_source_dedup_collapses_injected_duplicate(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_fixture_records(query, fixtures_dir=fixtures_dir)

    prov = Provenance(extractor="tests", fetched_at=datetime.now(UTC), query=query.serialize())
    mirror = VideoRecord(
        id="archive_org:mirror-wikimedia-carbonara",
        source="archive_org",
        source_native_id="mirror",
        url="https://archive.org/details/mirror",
        title="Cooking pasta carbonara",
        duration_s=312.0,
        author="Jane Cook",
        license=License.CC_BY_SA,
        provenance=prov,
    )
    by_source["archive_org"] = [*by_source["archive_org"], mirror]

    rows = run_comparison(query, by_source, notes="dedup-injected")
    total = next(r for r in rows if r.source == "__total__")
    assert total.n_records == sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_unique_after_dedup < total.n_records, (
        "Cross-source duplicate must collapse in the __total__ row"
    )
    assert total.dedup_rate > 0.0
