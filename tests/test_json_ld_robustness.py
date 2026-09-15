"""Adversarial guardrails for `parse_recipe_html`.

Real Common Crawl JSON-LD in the wild is dirty: authors invent `@type`
values, wrap `@graph` around themselves, embed cyclic references (illegal
per the spec but common in practice), and pass numeric values as strings
(and vice versa). This suite feeds intentionally-malformed payloads into
`parse_recipe_html` and asserts it never crashes and never emits a
`VideoRecord` that violates our Pydantic invariants.

If a case here starts *finding* records where it previously found none,
that is a *real* extraction win, not a test failure — update the
`assert_records_are_zero_or_valid` helper accordingly.
"""

from __future__ import annotations

from specint.records import SourceQuery, VideoRecord
from specint.sources.common_crawl import parse_recipe_html

QUERY = SourceQuery(terms=["cooking"], max_results=10)
PAGE = "https://example.test/broken-recipe"


def _html_with_jsonld(payload: str) -> str:
    return f'<html><body><script type="application/ld+json">{payload}</script></body></html>'


def _assert_records_are_zero_or_valid(records: list[VideoRecord]) -> None:
    for r in records:
        assert isinstance(r, VideoRecord)
        assert r.source == "common_crawl"
        assert r.id.startswith("common_crawl:")
        assert r.provenance.extractor
        assert r.duration_s is None or r.duration_s >= 0.0


def test_missing_type_field_does_not_crash():
    payload = '{"name": "no type", "duration": "PT5M"}'
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    assert records == []


def test_type_is_list_with_confusable_whitespace():
    payload = (
        '{"@type": ["Thing", "VideoObject "], "name": "Sneaky",'
        ' "duration": "PT2M", "contentUrl": "https://example.test/v.mp4"}'
    )
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)


def test_deeply_nested_graph_still_finds_video():
    payload = (
        '{"@context": "https://schema.org", "@graph": ['
        '  {"@type": "WebPage", "url": "https://example.test/broken-recipe"},'
        '  {"@type": "ItemList", "itemListElement": ['
        '    {"@type": "Recipe", "name": "Nested", "recipeInstructions":'
        '     "Do a thing. Then another."},'
        '    {"@type": "VideoObject", "name": "Nested Video",'
        '     "duration": "PT4M", "contentUrl": "https://example.test/v.mp4"}'
        "  ]}"
        "]}"
    )
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    assert len(records) == 1
    assert records[0].title == "Nested Video"
    assert records[0].duration_s == 240.0


def test_non_dict_entries_in_recipeinstructions_do_not_crash():
    payload = (
        '{"@context": "https://schema.org", "@graph": ['
        '  {"@type": "Recipe", "name": "Weird Steps",'
        '   "recipeInstructions": [1, null, "a real step", {"noText": true}]},'
        '  {"@type": "VideoObject", "name": "Weird Video",'
        '   "duration": "PT3M"}'
        "]}"
    )
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    assert records, "expected the VideoObject to still be extracted"
    steps = records[0].recipe_steps
    for s in steps:
        assert isinstance(s, str)
        assert s.strip(), "empty step strings must be filtered"


def test_duration_as_bare_number_yields_none():
    payload = '{"@type": "VideoObject", "name": "BadDur", "duration": 300}'
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    if records:
        assert records[0].duration_s is None


def test_multiple_videoobjects_extracted():
    payload = (
        "["
        '  {"@type": "VideoObject", "name": "First",  "duration": "PT2M"},'
        '  {"@type": "VideoObject", "name": "Second", "duration": "PT4M"}'
        "]"
    )
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    assert {r.title for r in records} == {"First", "Second"}


def test_broken_json_does_not_crash_page_parse():
    html = (
        "<html><body>"
        '<script type="application/ld+json">{not: json,,}</script>'
        '<script type="application/ld+json">'
        '{"@type": "VideoObject", "name": "Survivor", "duration": "PT1M"}'
        "</script>"
        "</body></html>"
    )
    records = parse_recipe_html(html, PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    assert len(records) == 1
    assert records[0].title == "Survivor"


def test_empty_script_tag_yields_no_records():
    html = '<html><body><script type="application/ld+json"></script></body></html>'
    records = parse_recipe_html(html, PAGE, QUERY)
    assert records == []


def test_video_with_no_name_or_duration_still_valid():
    payload = '{"@type": "VideoObject"}'
    records = parse_recipe_html(_html_with_jsonld(payload), PAGE, QUERY)
    _assert_records_are_zero_or_valid(records)
    if records:
        assert records[0].duration_s is None
        assert records[0].title == ""
