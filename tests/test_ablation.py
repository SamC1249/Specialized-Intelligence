from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_ablation
from specint.quality.metrics import WEIGHTS
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _all_sources(fixtures_dir: Path, query: SourceQuery) -> dict:
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


def test_ablation_reports_every_component(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _all_sources(fixtures_dir, query)

    payload = run_ablation(query, by_source, notes="test")

    assert set(payload["components"]) == set(WEIGHTS)
    baseline_mean = payload["baseline"]["mean_quality"]
    assert baseline_mean > 0.0

    for name, row in payload["components"].items():
        # Dropping a positive component never raises mean quality above baseline.
        assert row["mean_quality"] <= baseline_mean + 1e-9, name
        # license_clean is monotone: dropping any quality component cannot
        # change which records *are* license-clean (that's the records'
        # licence field, not the score).
        assert row["n_license_clean"] == payload["baseline"]["n_license_clean"]


def test_ablation_is_deterministic(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _all_sources(fixtures_dir, query)
    a = run_ablation(query, by_source, notes="test")
    b = run_ablation(query, by_source, notes="test")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
