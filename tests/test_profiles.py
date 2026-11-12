"""Profile invariants and v1-baseline regression test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from specint.compare import run_comparison
from specint.quality.profiles import COMPONENTS, PROFILES, score_with_profile
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def test_every_profile_sums_to_one() -> None:
    for name, weights in PROFILES.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"profile {name!r} weights sum to {total}"


def test_every_profile_references_registered_components() -> None:
    for name, weights in PROFILES.items():
        for comp in weights:
            assert comp in COMPONENTS, f"profile {name!r} references missing component {comp!r}"


def test_unknown_profile_raises() -> None:
    from datetime import datetime

    from specint.records import License, Provenance, VideoRecord

    r = VideoRecord(
        id="x:1",
        source="x",
        source_native_id="1",
        url="https://example.test/x",
        title="t",
        license=License.CC0,
        provenance=Provenance(extractor="x", fetched_at=datetime.fromtimestamp(0)),
    )
    with pytest.raises(KeyError):
        score_with_profile(r, profile="does-not-exist")


def test_v1_profile_reproduces_2026_06_20_baseline(fixtures_dir: Path) -> None:
    """Profile `v1` must match the committed baseline to the cent."""
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
    rows = run_comparison(query, by_source, notes="fixture-baseline", profile="v1")
    by_name = {r.source: r for r in rows}

    baseline = json.loads(
        Path(__file__).resolve().parents[1].joinpath("reports/baseline-2026-06-20.json").read_text()
    )
    for row in baseline["rows"]:
        actual = by_name[row["source"]]
        assert actual.n_records == row["n_records"]
        assert actual.n_license_clean == row["n_license_clean"]
        assert abs(actual.mean_quality - row["mean_quality"]) < 1e-9


def test_v2_differs_from_v1_on_relevant_record() -> None:
    from datetime import datetime

    from specint.records import License, Provenance, VideoRecord

    r = VideoRecord(
        id="x:1",
        source="x",
        source_native_id="1",
        url="https://example.test/x",
        title="Garlic Butter Pasta Recipe",
        description="A cooking tutorial with chef knife skills.",
        language="en",
        duration_s=300.0,
        height=1080,
        license=License.CC_BY,
        provenance=Provenance(extractor="x", fetched_at=datetime.fromtimestamp(0)),
    )
    v1 = score_with_profile(r, "v1")
    v2 = score_with_profile(r, "v2")
    v2c = score_with_profile(r, "v2_cooking")
    assert 0.0 <= v1 <= 1.0 and 0.0 <= v2 <= 1.0 and 0.0 <= v2c <= 1.0
    # Relevance-aware profiles should reward this record at least as much as v1.
    assert v2 >= v1 - 1e-6
    assert v2c >= v1 - 1e-6
