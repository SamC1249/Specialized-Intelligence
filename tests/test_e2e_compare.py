"""End-to-end test: run the full comparison harness against fixtures.

This is intentionally network-free. Each adapter's `parse` is invoked
against a checked-in fixture and the harness aggregates the results.
The test asserts the structural invariants we care about even as new
sources are added, plus a *regression guard* on total mean_quality so
future PRs cannot silently drift the score downwards.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import build_report, run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

# Regression guard. 2026-06-20 baseline mean_quality(__total__) was
# 0.499. The 2026-08-13 refactor lifted it to ~0.59. We assert a soft
# floor slightly below the 2026-06-20 baseline so any *future*
# regression fails CI while still allowing incremental scoring tweaks.
MEAN_QUALITY_FLOOR = 0.45


def _load_by_source(fixtures_dir: Path, query: SourceQuery):
    return {
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


def test_e2e_offline_compare_across_all_sources(fixtures_dir: Path, tmp_path: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)

    by_source = _load_by_source(fixtures_dir, query)
    rows = run_comparison(query, by_source, notes="e2e-fixture")

    sources_seen = {row.source for row in rows}
    assert sources_seen == {"wikimedia", "archive_org", "peertube", "common_crawl", "__total__"}

    total = next(r for r in rows if r.source == "__total__")
    per_source_total = sum(r.n_records for r in rows if r.source != "__total__")
    assert total.n_records == per_source_total
    assert total.n_records > 0

    for row in rows:
        assert row.n_license_clean <= row.n_records
        assert 0.0 <= row.mean_quality <= 1.0

    assert total.mean_quality >= MEAN_QUALITY_FLOOR, (
        f"mean_quality regressed: {total.mean_quality} < floor {MEAN_QUALITY_FLOOR}"
    )

    payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    out = tmp_path / "compare.json"
    out.write_text(json.dumps(payload, sort_keys=True))
    reloaded = json.loads(out.read_text())
    assert reloaded["query"]["terms"] == ["cooking", "recipe"]
    assert len(reloaded["rows"]) == 5


def test_e2e_dedupe_collapses_planted_cross_source_duplicate(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_by_source(fixtures_dir, query)

    payload = build_report(query, by_source, dedupe_enabled=True)
    overlap = payload["overlap"]
    total_row = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total_row["n_duplicates"] >= 1
    assert overlap["total_records"] > overlap["unique_fingerprints"]

    wm_ia_pair = next(
        p for p in overlap["pairs"] if {p["a"], p["b"]} == {"wikimedia", "archive_org"}
    )
    assert wm_ia_pair["shared"] >= 1


def test_e2e_multilingual_records_score_language_confidence(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _load_by_source(fixtures_dir, query)
    payload = build_report(query, by_source, dedupe_enabled=False)
    for row in payload["rows"]:
        assert 0.0 <= row["mean_language_confidence"] <= 1.0
    total_row = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total_row["mean_language_confidence"] > 0.3
