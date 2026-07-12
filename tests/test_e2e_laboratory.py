"""Proves H1: the pipeline generalises to a non-cooking domain.

We feed a `laboratory` fixture set through the same harness, using the
laboratory domain's procedural verb list, and assert the same structural
invariants hold.
"""

from __future__ import annotations

import json
from pathlib import Path

from specint.compare import run_comparison
from specint.domains import LABORATORY
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


def test_laboratory_pipeline_produces_records_and_deduped_totals(fixtures_dir: Path):
    query = SourceQuery(terms=list(LABORATORY.seed_terms[:2]), max_results=25)

    by_source = {
        "wikimedia": WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_lab.json").read_text()), query
        ),
        "archive_org": ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_lab.json").read_text()), query
        ),
        "peertube": PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_lab.json").read_text()), query
        ),
        "common_crawl": CommonCrawlRecipeSource().parse(
            {
                "html": (fixtures_dir / "common_crawl/lab_protocol.html").read_text(),
                "url": "https://example.test/protocols/enzyme-kinetics",
            },
            query,
        ),
    }

    rows = run_comparison(query, by_source, notes="e2e-lab", domain=LABORATORY)

    slugs = {row.source for row in rows}
    assert {"wikimedia", "archive_org", "peertube", "common_crawl"}.issubset(slugs)
    assert "__total__" in slugs
    assert "__total_deduped__" in slugs

    per_source = [r for r in rows if not r.source.startswith("__")]
    assert sum(r.n_records for r in per_source) > 0
    assert sum(r.n_license_clean for r in per_source) > 0

    for row in per_source:
        assert row.n_license_clean <= row.n_records
