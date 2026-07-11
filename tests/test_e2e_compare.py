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

    # New cross-source dedup columns must be populated and sane.
    for row in rows:
        assert row.n_unique_across_sources is not None
        assert row.duplicate_rate is not None
        assert row.unique_duration_s is not None
        assert 0 <= row.n_unique_across_sources <= row.n_records
        assert 0.0 <= row.duplicate_rate <= 1.0
        assert row.unique_duration_s <= row.total_duration_s + 1e-6

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


def test_e2e_cross_source_dedup_actually_deduplicates(fixtures_dir: Path):
    """If the same video ends up on two sources it must be deduped in `__total__`."""
    query = SourceQuery(terms=["cooking"], max_results=25)
    wiki_records = json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())
    parsed_wiki = json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())
    from specint.sources.wikimedia import WikimediaCommonsSource as W

    orig = W().parse(wiki_records, query)
    mirrored = W().parse(parsed_wiki, query)
    # Rename mirrored to look like a different source's ids so aggregate
    # treats them as distinct rows but dedup still catches them.
    mirrored = [
        r.model_copy(update={"id": f"archive_org:{r.source_native_id}", "source": "archive_org"})
        for r in mirrored
    ]
    rows = run_comparison(
        query,
        {"wikimedia": orig, "archive_org": mirrored},
        notes="dedup-e2e",
    )
    total = next(r for r in rows if r.source == "__total__")
    assert total.n_records == len(orig) + len(mirrored)
    assert total.n_unique_across_sources is not None
    assert total.n_unique_across_sources < total.n_records
    assert total.duplicate_rate and total.duplicate_rate > 0.0
