import json
from pathlib import Path

from specint.compare.ablation import run_ablation
from specint.quality.metrics import SCORING_PROFILES
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def _fixture_by_source(fixtures_dir: Path, query: SourceQuery):
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


def test_run_ablation_covers_all_default_profiles(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = _fixture_by_source(fixtures_dir, query)

    payload = run_ablation(query, by_source, notes="test")
    assert set(payload["profiles"].keys()) == set(SCORING_PROFILES.keys())
    for name, block in payload["profiles"].items():
        assert block["weights"] == SCORING_PROFILES[name]
        assert isinstance(block["rows"], list)
        assert len(block["rows"]) == len(by_source) + 1  # + __total__
        assert isinstance(block["ranking"], list)
        assert set(block["ranking"]) == set(by_source.keys())


def test_ablation_profiles_can_disagree_on_ranking(fixtures_dir: Path):
    query = SourceQuery(terms=["cooking"], max_results=25)
    by_source = _fixture_by_source(fixtures_dir, query)
    payload = run_ablation(query, by_source)
    rankings = {tuple(p["ranking"]) for p in payload["profiles"].values()}
    assert len(rankings) >= 1
    assert payload["ranking_agreement"] == (len(rankings) == 1)


def test_ablation_rejects_unknown_profile(fixtures_dir: Path):
    query = SourceQuery(terms=["a"], max_results=1)
    by_source = _fixture_by_source(fixtures_dir, query)
    try:
        run_ablation(query, by_source, profiles=["balanced", "nope"])
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError for unknown profile")
