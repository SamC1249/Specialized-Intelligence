import json
from pathlib import Path

from specint.compare import PRESETS, run_ablation
from specint.quality.metrics import WEIGHTS
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource
from specint.sources.youtube_cc import YouTubeCCSource


def _all_records(fixtures_dir: Path, query: SourceQuery) -> dict[str, list]:
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
        "youtube_cc": YouTubeCCSource().parse(
            json.loads((fixtures_dir / "youtube_cc/videos_cooking.json").read_text()), query
        ),
    }


def test_ablation_runs_every_preset(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    bundle = run_ablation(query, _all_records(fixtures_dir, query))
    assert set(bundle["presets"]) == set(PRESETS)
    for preset in bundle["presets"].values():
        assert "weights" in preset
        assert 0.0 <= preset["total_mean_quality"] <= 1.0
        assert preset["total_n_license_clean"] >= 0


def test_ablation_no_license_preset_lowers_score_vs_baseline(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    bundle = run_ablation(query, _all_records(fixtures_dir, query))
    baseline = bundle["presets"]["baseline"]["total_mean_quality"]
    no_lic = bundle["presets"]["no_license"]["total_mean_quality"]
    assert no_lic < baseline + 1e-9


def test_ablation_does_not_mutate_module_weights(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    snapshot = dict(WEIGHTS)
    run_ablation(query, _all_records(fixtures_dir, query))
    assert dict(WEIGHTS) == snapshot
