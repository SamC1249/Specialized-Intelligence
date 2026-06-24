"""End-to-end pipeline determinism + provenance test.

This test guarantees that running ``scripts/pipeline_dry_run.py`` twice
against the same fixtures produces byte-for-byte identical manifests
and reports — a precondition for the comparison-first workflow in
``AGENTS.md``.

It also exercises the blocklist integration: applying the YouCook2-shaped
fixture must drop the contaminated record from the manifest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture
def fixtures_dir() -> Path:
    return REPO_ROOT / "tests" / "fixtures"


def test_pipeline_dry_run_is_deterministic(tmp_path: Path, fixtures_dir: Path):
    from pipeline_dry_run import dry_run

    manifest_a = tmp_path / "a.jsonl"
    report_a = tmp_path / "a.json"
    summary_a = dry_run(
        fixtures_dir=fixtures_dir,
        manifest_path=manifest_a,
        report_path=report_a,
    )

    manifest_b = tmp_path / "b.jsonl"
    report_b = tmp_path / "b.json"
    summary_b = dry_run(
        fixtures_dir=fixtures_dir,
        manifest_path=manifest_b,
        report_path=report_b,
    )

    assert summary_a["manifest_sha256"] == summary_b["manifest_sha256"]
    assert summary_a["report_sha256"] == summary_b["report_sha256"]
    assert manifest_a.read_text() == manifest_b.read_text()
    assert report_a.read_text() == report_b.read_text()

    # Manifest must be one valid VideoRecord JSON per line.
    for line in manifest_a.read_text().splitlines():
        payload = json.loads(line)
        assert payload["source"] in {"wikimedia", "archive_org", "peertube", "common_crawl"}
        assert "provenance" in payload
        assert "quality_score" in payload
        assert 0.0 <= payload["license_confidence"] <= 1.0


def test_pipeline_dry_run_blocklist_drops_overlap(tmp_path: Path, fixtures_dir: Path):
    from pipeline_dry_run import dry_run

    # Forge a blocklist that hits one of the wikimedia fixture records.
    blocklist = tmp_path / "blocklist.jsonl"
    blocklist.write_text('{"kind": "title_norm", "value": "File:Cooking pasta carbonara.webm"}\n')

    summary_no_block = dry_run(
        fixtures_dir=fixtures_dir,
        manifest_path=tmp_path / "no.jsonl",
        report_path=tmp_path / "no.json",
    )
    summary_with_block = dry_run(
        fixtures_dir=fixtures_dir,
        blocklist_path=blocklist,
        manifest_path=tmp_path / "yes.jsonl",
        report_path=tmp_path / "yes.json",
    )

    assert int(summary_with_block["n_records"]) <= int(summary_no_block["n_records"])
    # With a real overlap the dropped count must be positive.
    assert int(summary_with_block["n_dropped"]) >= 1
