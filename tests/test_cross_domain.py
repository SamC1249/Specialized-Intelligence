"""Retarget the harness to a non-cooking domain.

AGENTS.md: "every system must generalize to other 'difficult video'
domains (surgery, lab work, sports, manufacturing, etc.)". Ensure the
pipeline is domain-agnostic — swap seed terms and the harness must
still produce structurally valid `BenchmarkResult` rows even when the
fixture returns zero matches for that domain.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.compare import run_comparison
from specint.records import SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource


@pytest.mark.parametrize(
    "domain_terms",
    [
        ["surgery", "laparoscopic"],
        ["welding", "manufacturing"],
        ["chemistry", "titration"],
    ],
)
def test_harness_is_domain_agnostic(fixtures_dir: Path, domain_terms: list[str]):
    query = SourceQuery(terms=domain_terms, max_results=25)

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
    }

    rows = run_comparison(query, by_source, notes=f"cross-domain:{domain_terms[0]}")
    seen = {r.source for r in rows}
    assert "__total__" in seen
    for r in rows:
        assert r.query_terms == domain_terms
        assert r.n_license_clean <= r.n_records
        assert r.p50_quality <= r.p90_quality + 1e-9
        assert r.total_duration_s >= 0.0
