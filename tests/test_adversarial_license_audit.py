"""Adversarial license-audit test.

Purpose: pressure-test each adapter's fixture round-trip so we catch
regressions the moment an adapter silently degrades license
classification (e.g. starts labelling everything `License.UNKNOWN`, or
emits `media_url` for a restricted licence, or forgets author on
CC-BY).

Sources included in the audit must be listed in `_AUDIT_SPECS` with an
explicit expectation about how many license-clean records their
fixture should produce; this doubles as the *baseline count* that a
future PR must justify changing.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from specint.records import License, SourceQuery, VideoRecord
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

ATTRIBUTION_REQUIRED = {License.CC_BY, License.CC_BY_SA}
KNOWN_UNKNOWN_OK = {"common_crawl"}


@dataclass(frozen=True)
class AuditSpec:
    slug: str
    fixture: str
    build: Callable[[Path, SourceQuery], list[VideoRecord]]
    expected_records: int
    expected_license_clean: int
    max_unknown: int


def _wikimedia(fixtures_dir: Path, q: SourceQuery) -> list[VideoRecord]:
    raw = json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())
    return WikimediaCommonsSource().parse(raw, q)


def _archive(fixtures_dir: Path, q: SourceQuery) -> list[VideoRecord]:
    raw = json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text())
    return ArchiveOrgSource().parse(raw, q)


def _peertube(fixtures_dir: Path, q: SourceQuery) -> list[VideoRecord]:
    raw = json.loads((fixtures_dir / "peertube/search_cooking.json").read_text())
    return PeerTubeSource().parse(raw, q)


def _common_crawl(fixtures_dir: Path, q: SourceQuery) -> list[VideoRecord]:
    raw: dict[str, Any] = {
        "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
        "url": "https://example.test/recipes/garlic-butter-pasta",
    }
    return CommonCrawlRecipeSource().parse(raw, q)


_AUDIT_SPECS: list[AuditSpec] = [
    AuditSpec("wikimedia", "wikimedia/search_pasta.json", _wikimedia, 2, 2, 0),
    AuditSpec("archive_org", "archive_org/search_cooking.json", _archive, 3, 2, 0),
    AuditSpec("peertube", "peertube/search_cooking.json", _peertube, 2, 2, 0),
    AuditSpec("common_crawl", "common_crawl/recipe_page.html", _common_crawl, 1, 0, 1),
]


@pytest.mark.parametrize("spec", _AUDIT_SPECS, ids=lambda s: s.slug)
def test_fixture_license_audit(fixtures_dir: Path, spec: AuditSpec) -> None:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    records = spec.build(fixtures_dir, query)

    assert len(records) == spec.expected_records, (
        f"{spec.slug}: expected {spec.expected_records} records, got {len(records)}. "
        "If you changed a fixture or parser, update _AUDIT_SPECS deliberately."
    )

    clean = [r for r in records if r.license.is_redistributable]
    assert len(clean) == spec.expected_license_clean, (
        f"{spec.slug}: license-clean count regressed to {len(clean)} "
        f"(expected {spec.expected_license_clean})."
    )

    unknowns = [r for r in records if r.license is License.UNKNOWN]
    if spec.slug not in KNOWN_UNKNOWN_OK:
        assert unknowns == [], (
            f"{spec.slug}: {len(unknowns)} record(s) parsed to License.UNKNOWN. "
            "That is a silent regression — either fix classification or add "
            "the source to KNOWN_UNKNOWN_OK with a documented reason."
        )
    assert len(unknowns) <= spec.max_unknown, (
        f"{spec.slug}: {len(unknowns)} UNKNOWN records exceeds the audit cap of {spec.max_unknown}."
    )

    for r in records:
        if r.license in ATTRIBUTION_REQUIRED:
            assert r.author, (
                f"{spec.slug}: record {r.id} claims {r.license.value} but has no author. "
                "Attribution licenses require a non-empty author string."
            )
        if r.license is License.RESTRICTED:
            assert r.media_url is None, (
                f"{spec.slug}: record {r.id} is RESTRICTED but exposes media_url; "
                "we must never advertise a direct media URL for restricted content."
            )
        if r.license is License.UNKNOWN:
            assert r.media_url is None, (
                f"{spec.slug}: record {r.id} has UNKNOWN license but a media_url; "
                "media_url is only allowed on redistributable licenses."
            )


def test_attribution_licenses_never_lose_author_across_all_sources(fixtures_dir: Path) -> None:
    query = SourceQuery(terms=["cooking"], max_results=25)
    for spec in _AUDIT_SPECS:
        for r in spec.build(fixtures_dir, query):
            if r.license in ATTRIBUTION_REQUIRED and not r.author:
                pytest.fail(
                    f"{spec.slug}:{r.source_native_id}: attribution required "
                    f"but author is empty ({r.license.value})."
                )
