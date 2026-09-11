"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.records import SourceQuery
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


def test_e2e_dedup_and_v2_profile(fixtures_dir: Path):
    """Ship the dupe fixtures through the CLI-style loader path.

    We invoke the harness directly (not the CLI) but load *all* JSON /
    HTML files per source, exactly like `python -m specint compare
    --fixtures` does.
    """
    import json as _json

    from specint.compare import run_comparison
    from specint.records import SourceQuery

    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)

    def _load_json_dir(sub: str, cls):
        parsed = []
        for p in sorted((fixtures_dir / sub).glob("*.json")):
            parsed.extend(cls().parse(_json.loads(p.read_text()), query))
        return parsed

    by_source = {
        "wikimedia": _load_json_dir("wikimedia", WikimediaCommonsSource),
        "archive_org": _load_json_dir("archive_org", ArchiveOrgSource),
        "peertube": _load_json_dir("peertube", PeerTubeSource),
        "common_crawl": [
            *CommonCrawlRecipeSource().parse(
                {
                    "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
                    "url": "https://example.test/recipes/garlic-butter-pasta",
                },
                query,
            )
        ],
    }

    v1_no_dedup = run_comparison(query, by_source, notes="e2e", profile="v1", dedup=False)
    v1_dedup = run_comparison(query, by_source, notes="e2e", profile="v1", dedup=True)
    v2_dedup = run_comparison(query, by_source, notes="e2e", profile="v2", dedup=True)

    total_no_dedup = next(r for r in v1_no_dedup if r.source == "__total__")
    total_dedup = next(r for r in v1_dedup if r.source == "__total__")

    # The NASA fixture is intentionally mirrored across wikimedia and
    # archive_org — dedup must drop at least one record.
    assert total_dedup.n_unique < total_no_dedup.n_records
    assert total_dedup.duplicate_rate > 0.0

    for row in v2_dedup:
        assert row.profile == "v2"
        assert 0.0 <= row.mean_quality <= 1.0
