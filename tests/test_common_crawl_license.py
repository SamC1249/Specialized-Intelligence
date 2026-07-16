from __future__ import annotations

from specint.records import License, SourceQuery
from specint.sources.common_crawl import parse_recipe_html


def test_cc_licensed_recipe_lifts_out_of_unknown(load_text):
    html = load_text("common_crawl/cc_licensed_recipe.html")
    records = parse_recipe_html(
        html,
        page_url="https://wikibooks-cookbook.example/cc-lasagna",
        query=SourceQuery(terms=["lasagna"]),
    )
    assert len(records) == 1
    r = records[0]
    assert r.license is License.CC_BY_SA
    assert r.license_url is not None
    assert "creativecommons.org" in str(r.license_url)
    assert r.media_url is not None
    assert r.duration_s == 372.0
    assert len(r.recipe_steps) == 5


def test_original_recipe_page_stays_unknown_without_evidence(load_text):
    """The pre-existing fixture ships no license markup. We must not
    upgrade it — this is the H4 mitigation.
    """
    html = load_text("common_crawl/recipe_page.html")
    records = parse_recipe_html(
        html,
        page_url="https://example.test/recipes/garlic-butter-pasta",
        query=SourceQuery(terms=["pasta"]),
    )
    assert len(records) == 1
    assert records[0].license is License.UNKNOWN
    assert records[0].media_url is None


def test_single_signal_is_insufficient_to_upgrade():
    """Only one CC URL is present → stay UNKNOWN."""
    html = (
        '<html><head><link rel="license" '
        'href="https://creativecommons.org/licenses/by/4.0/"></head>'
        '<body><script type="application/ld+json">'
        '{"@type":"VideoObject","name":"x","duration":"PT2M"}'
        "</script></body></html>"
    )
    records = parse_recipe_html(html, "https://ex.test/x", SourceQuery(terms=["x"]))
    assert len(records) == 1
    assert records[0].license is License.UNKNOWN
