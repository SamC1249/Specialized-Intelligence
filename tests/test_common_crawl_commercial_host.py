"""Confirm that VideoObjects pointing at commercial hosts stay RESTRICTED."""

from __future__ import annotations

from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.common_crawl import (
    COMMERCIAL_VIDEO_HOSTS,
    CommonCrawlRecipeSource,
    parse_recipe_html,
)


def test_youtube_embed_marked_restricted(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "common_crawl/recipe_page_youtube_embed.html").read_text()
    records = parse_recipe_html(
        html,
        "https://example.test/recipes/broccoli-cheddar-soup",
        SourceQuery(terms=["soup"]),
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.license is License.RESTRICTED
    assert rec.media_url is None


def test_source_wrapper_passes_through_commercial_detection(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "common_crawl/recipe_page_youtube_embed.html").read_text()
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://example.test/recipes/broccoli-cheddar-soup"},
        SourceQuery(terms=["soup"]),
    )
    assert records[0].license is License.RESTRICTED


def test_known_hosts_list_includes_core_platforms() -> None:
    for host in ("youtube.com", "vimeo.com", "tiktok.com", "facebook.com"):
        assert host in COMMERCIAL_VIDEO_HOSTS
