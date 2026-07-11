"""Property-based tests for the Common Crawl JSON-LD parser.

Attack: independent of what garbage JSON-LD a scraped recipe page
contains, the Common Crawl parser must never crash and must never
promote a record to a redistributable license. Page license integrity
is the responsibility of a separate step (see the 2026-06-20 seed plan);
the parser itself is *not allowed* to invent one.
"""

from __future__ import annotations

import json

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from specint.records import License, SourceQuery
from specint.sources.common_crawl import parse_recipe_html

QUERY = SourceQuery(terms=["cooking"], max_results=25)

_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-10_000, max_value=10_000),
    st.text(min_size=0, max_size=40),
)


def _jsonld_dict():
    return st.dictionaries(
        keys=st.sampled_from(
            [
                "@type",
                "name",
                "description",
                "duration",
                "contentUrl",
                "embedUrl",
                "identifier",
                "uploadDate",
                "recipeInstructions",
                "keywords",
                "width",
                "height",
                "author",
            ]
        ),
        values=st.one_of(_scalar, st.lists(_scalar, max_size=3)),
        max_size=6,
    )


@settings(
    deadline=None,
    max_examples=75,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
@given(
    st.lists(_jsonld_dict(), min_size=0, max_size=4),
    st.text(min_size=1, max_size=40),
)
def test_parser_never_crashes_and_never_promotes_license(blocks, page_slug):
    for block in blocks:
        block.setdefault("@type", "VideoObject")
    html = (
        "<html><body>"
        f'<script type="application/ld+json">{json.dumps(blocks)}</script>'
        "</body></html>"
    )
    page_url = f"https://example.test/recipes/{page_slug.replace(' ', '-')}"
    records = parse_recipe_html(html, page_url, QUERY)
    for r in records:
        assert r.license is License.UNKNOWN, (
            "Common Crawl parser must default license to UNKNOWN; page-level "
            "license proof lives elsewhere in the pipeline."
        )
        assert r.media_url is None, "UNKNOWN-licensed records must never expose media_url"


@given(st.text(min_size=0, max_size=200))
def test_parser_handles_malformed_json_gracefully(garbage):
    html = f'<html><body><script type="application/ld+json">{garbage}</script></body></html>'
    records = parse_recipe_html(html, "https://example.test/malformed", QUERY)
    for r in records:
        assert r.license is License.UNKNOWN
