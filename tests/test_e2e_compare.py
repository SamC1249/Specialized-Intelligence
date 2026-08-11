"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import load_fixture_by_source, run_comparison
from specint.records import SourceQuery


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_fixture_by_source(fixtures_dir, query)

    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {"wikimedia", "archive_org", "peertube", "common_crawl", "__total__"}

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    for row in rows:
        assert row.n_license_clean <= row.n_records

    # 2026-08-11 additions:
    #   - The __total__ row now reports dedup + language-confidence stats.
    #   - Wikimedia + archive_org fixtures share a "Modern Chef Demonstration"
    #     record so cross-source dedup fires.
    assert total.n_after_dedup is not None
    assert total.cross_source_duplicates is not None
    assert total.n_after_dedup <= total.n_records
    assert total.cross_source_duplicates >= 1
    assert total.mean_language_confidence is not None
    assert total.mean_language_confidence > 0.0

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == 5
