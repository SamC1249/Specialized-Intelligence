"""Tests for `specint.quality.profiles`.

Includes the comparison-first regression guard required by AGENTS.md:
on the shared offline fixtures the `v2` profile must not regress the
`baseline` profile's mean quality.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from specint._fixtures import load_fixtures
from specint.compare import run_comparison
from specint.quality.profiles import PROFILES, QualityProfile, get_profile
from specint.records import License, Provenance, SourceQuery, VideoRecord

FIXTURES = Path(__file__).parent / "fixtures"
BASELINE_REPORT = Path(__file__).resolve().parents[1] / "reports" / "baseline-2026-06-20.json"


def _rec(**kw):
    defaults = dict(
        id="test:1",
        source="test",
        source_native_id="1",
        url="https://example.test/1",
        title="Cooking demo",
        description="",
        provenance=Provenance(extractor="test", fetched_at=datetime(2026, 1, 1, tzinfo=UTC)),
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
    )
    defaults.update(kw)
    return VideoRecord(**defaults)


def test_profiles_registered():
    assert "baseline" in PROFILES
    assert "v2" in PROFILES
    assert all(isinstance(p, QualityProfile) for p in PROFILES.values())


def test_get_profile_unknown_raises():
    try:
        get_profile("nope")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_profile_score_is_in_unit_interval():
    r = _rec()
    for p in PROFILES.values():
        s = p.score(r)
        assert 0.0 <= s <= 1.0


def test_baseline_profile_reproduces_june_report():
    """`baseline` must still produce the mean-quality numbers committed
    in `reports/baseline-2026-06-20.json`. If this test fails someone
    changed the frozen baseline."""
    baseline_report = json.loads(BASELINE_REPORT.read_text())
    baseline_rows = {row["source"]: row for row in baseline_report["rows"]}

    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    # Use the original single-fixture-per-source set the June report used
    # (we have added multilingual fixtures since then; restrict here).
    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((FIXTURES / "wikimedia/search_pasta.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((FIXTURES / "archive_org/search_cooking.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((FIXTURES / "peertube/search_cooking.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (FIXTURES / "common_crawl/recipe_page.html").read_text(),
                "url": "https://example.test/recipes/garlic-butter-pasta",
            },
            query,
        ),
    }
    rows = run_comparison(query, by_source, notes="fixture-baseline", profile="baseline")
    for row in rows:
        if row.source not in baseline_rows:
            continue
        expected = baseline_rows[row.source]
        assert abs(row.mean_quality - expected["mean_quality"]) < 1e-9, (
            f"baseline drift on {row.source}: {row.mean_quality} vs {expected['mean_quality']}"
        )


def test_v2_does_not_regress_baseline_on_shared_fixtures():
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    by_source = load_fixtures(query)

    baseline_rows = {r.source: r for r in run_comparison(query, by_source, profile="baseline")}
    v2_rows = {r.source: r for r in run_comparison(query, by_source, profile="v2")}

    for source, b_row in baseline_rows.items():
        v = v2_rows[source]
        if b_row.n_records == 0:
            continue
        # license_clean recall must not drop
        assert v.n_license_clean == b_row.n_license_clean, source
        # cross-source __total__ mean must strictly improve under v2
        if source == "__total__":
            assert v.mean_quality >= b_row.mean_quality
