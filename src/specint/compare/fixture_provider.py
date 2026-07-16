"""Fixture-driven record provider for the offline CLI.

The Adversarial-Agent 2026-07-14 (6c76) plan called out that
`python -m specint compare --fixtures` was returning an all-zeros
report because the CLI never actually loaded fixture data. This
module fixes that by discovering the checked-in `tests/fixtures/`
tree and running each adapter's pure `parse()` against it.

The provider is deliberately I/O-only at construction time — no
network — so it can be reused by both the CLI and the offline e2e
test.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from specint.records import SourceQuery, VideoRecord
from specint.sources import (
    REGISTRY,
    ArchiveOrgSource,
    CommonCrawlRecipeSource,
    PeerTubeSource,
    WikimediaCommonsSource,
)

DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


ParseFn = Callable[[Any, SourceQuery], list[VideoRecord]]


def _wikimedia_parse(raw: Any, query: SourceQuery) -> list[VideoRecord]:
    return WikimediaCommonsSource().parse(raw, query)


def _archive_parse(raw: Any, query: SourceQuery) -> list[VideoRecord]:
    return ArchiveOrgSource().parse(raw, query)


def _peertube_parse(raw: Any, query: SourceQuery) -> list[VideoRecord]:
    return PeerTubeSource().parse(raw, query)


def _common_crawl_parse(raw: Any, query: SourceQuery) -> list[VideoRecord]:
    return CommonCrawlRecipeSource().parse(raw, query)


# Each entry is a list of (relative fixture path, loader, page_url).
# `page_url` is only used by common_crawl.
FIXTURE_MANIFEST: dict[str, list[tuple[str, str, str | None]]] = {
    "wikimedia": [
        ("wikimedia/search_pasta.json", "json", None),
        ("wikimedia/multilingual.json", "json", None),
    ],
    "archive_org": [
        ("archive_org/search_cooking.json", "json", None),
    ],
    "peertube": [
        ("peertube/search_cooking.json", "json", None),
        ("peertube/restricted_licence.json", "json", None),
    ],
    "common_crawl": [
        (
            "common_crawl/recipe_page.html",
            "html",
            "https://example.test/recipes/garlic-butter-pasta",
        ),
        (
            "common_crawl/cc_licensed_recipe.html",
            "html",
            "https://wikibooks-cookbook.example/cc-lasagna",
        ),
    ],
}


_PARSERS: dict[str, ParseFn] = {
    "wikimedia": _wikimedia_parse,
    "archive_org": _archive_parse,
    "peertube": _peertube_parse,
    "common_crawl": _common_crawl_parse,
}


def _load_fixture(root: Path, rel: str, kind: str, page_url: str | None) -> Any:
    path = root / rel
    if kind == "json":
        return json.loads(path.read_text())
    if kind == "html":
        return {"html": path.read_text(), "url": page_url}
    raise ValueError(f"unknown fixture kind: {kind}")


def load_records_by_source(
    query: SourceQuery,
    root: Path | None = None,
    only: set[str] | None = None,
) -> dict[str, list[VideoRecord]]:
    """Return `{slug: records}` by running each adapter's parse
    against every fixture listed in `FIXTURE_MANIFEST`. Missing
    fixture files raise `FileNotFoundError`; missing entries in
    `FIXTURE_MANIFEST` are silently skipped (which surfaces if we
    ever register a new source without wiring its fixture).
    """
    root = (root or DEFAULT_FIXTURE_ROOT).resolve()
    by_source: dict[str, list[VideoRecord]] = {}
    for slug in REGISTRY:
        if only and slug not in only:
            continue
        entries = FIXTURE_MANIFEST.get(slug, [])
        parser = _PARSERS[slug]
        records: list[VideoRecord] = []
        for rel, kind, page_url in entries:
            raw = _load_fixture(root, rel, kind, page_url)
            records.extend(parser(raw, query))
        by_source[slug] = records
    return by_source


def load_suite(
    root: Path | None = None,
) -> Mapping[str, dict[str, list[VideoRecord]]]:
    """Multi-query variant used by `run_matrix` and the matrix CLI.

    Reads `tests/fixtures/suite/query_suite.json` — a small JSON
    array of queries and the fixture files each query should be
    treated as covering. Everything is offline and deterministic.
    """
    root = (root or DEFAULT_FIXTURE_ROOT).resolve()
    suite_path = root / "suite" / "query_suite.json"
    payload = json.loads(suite_path.read_text())

    by_query_source: dict[str, dict[str, list[VideoRecord]]] = {}
    for entry in payload.get("queries", []):
        terms = entry["terms"]
        query = SourceQuery(terms=terms, max_results=int(entry.get("max_results", 25)))
        by_source: dict[str, list[VideoRecord]] = {}
        for slug, fixtures in entry.get("fixtures", {}).items():
            if slug not in _PARSERS:
                continue
            parser = _PARSERS[slug]
            records: list[VideoRecord] = []
            for spec in fixtures:
                kind = spec["kind"]
                page_url = spec.get("page_url")
                raw = _load_fixture(root, spec["path"], kind, page_url)
                records.extend(parser(raw, query))
            by_source[slug] = records
        by_query_source[query.serialize()] = by_source
    return by_query_source
