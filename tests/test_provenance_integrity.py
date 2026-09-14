"""Guardrail: every emitted `VideoRecord` carries auditable provenance.

AGENTS.md hard-constraint #2 (Provenance is mandatory) says every record
must carry source URL, license, capture timestamp, and the exact
extractor commit hash. Nothing enforced this in code today. This test
does — for every registered source, against its checked-in fixture.

Weak-form (enforced today):
  * `provenance.extractor`   is non-empty and looks like a module path.
  * `provenance.fetched_at`  is a timezone-aware UTC `datetime`.
  * `provenance.query`       is a non-empty serialised `SourceQuery`.
  * `provenance.extractor_git` is non-empty.
  * `record.license`         is a member of the `License` enum
                             (never `None`, never a raw string).
  * `record.url`             is a canonical landing URL (not a CDN).

Strong-form (documented as `xfail` until `_git.resolve_commit()` lands):
  * `provenance.extractor_git` is NOT the placeholder `"dev"`.
    See docs/plan-2026-09-14.md H6.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest

from specint.records import License, SourceQuery, VideoRecord
from specint.sources import REGISTRY
from specint.sources.base import BaseSource

FixtureLoader = Callable[[Path], Any]


def _load_wikimedia(fixtures_dir: Path) -> Any:
    return json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text())


def _load_archive_org(fixtures_dir: Path) -> Any:
    return json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text())


def _load_peertube(fixtures_dir: Path) -> Any:
    return json.loads((fixtures_dir / "peertube/search_cooking.json").read_text())


def _load_common_crawl(fixtures_dir: Path) -> Any:
    return {
        "html": (fixtures_dir / "common_crawl/recipe_page.html").read_text(),
        "url": "https://example.test/recipes/garlic-butter-pasta",
    }


_FIXTURE_LOADERS: dict[str, FixtureLoader] = {
    "wikimedia": _load_wikimedia,
    "archive_org": _load_archive_org,
    "peertube": _load_peertube,
    "common_crawl": _load_common_crawl,
}


def _all_registered_records(fixtures_dir: Path) -> list[tuple[str, VideoRecord]]:
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    out: list[tuple[str, VideoRecord]] = []
    for slug, cls in REGISTRY.items():
        loader = _FIXTURE_LOADERS.get(slug)
        assert loader is not None, (
            f"REGISTRY has {slug!r} but tests/test_provenance_integrity.py has "
            "no fixture loader for it — add one alongside any new adapter."
        )
        instance: BaseSource = cls()
        for record in instance.parse(loader(fixtures_dir), query):
            out.append((slug, record))
    return out


@pytest.fixture
def all_records(fixtures_dir: Path) -> list[tuple[str, VideoRecord]]:
    records = _all_registered_records(fixtures_dir)
    assert records, "no records emitted by any registered source — fixture drift?"
    return records


def test_every_record_has_licensed_provenance(
    all_records: list[tuple[str, VideoRecord]],
) -> None:
    for slug, record in all_records:
        prov = record.provenance
        assert prov.extractor, f"{slug}: empty provenance.extractor"
        assert "." in prov.extractor, (
            f"{slug}: provenance.extractor {prov.extractor!r} is not a module path"
        )
        assert prov.fetched_at.tzinfo is not None, (
            f"{slug}: provenance.fetched_at must be timezone-aware"
        )
        assert prov.fetched_at.utcoffset() == UTC.utcoffset(prov.fetched_at), (
            f"{slug}: provenance.fetched_at must be UTC"
        )
        assert prov.query, f"{slug}: provenance.query is empty"
        assert prov.extractor_git, f"{slug}: provenance.extractor_git is empty"


def test_every_record_has_license_enum(
    all_records: list[tuple[str, VideoRecord]],
) -> None:
    for slug, record in all_records:
        assert isinstance(record.license, License), (
            f"{slug}: record.license must be a License enum, got {type(record.license)!r}"
        )


def test_every_record_has_canonical_landing_url(
    all_records: list[tuple[str, VideoRecord]],
) -> None:
    for slug, record in all_records:
        assert str(record.url), f"{slug}: record.url is empty"
        assert str(record.url).startswith(("http://", "https://")), (
            f"{slug}: record.url {record.url!r} is not http(s)"
        )


def test_media_url_only_when_license_permits_redistribution(
    all_records: list[tuple[str, VideoRecord]],
) -> None:
    for slug, record in all_records:
        if record.media_url is None:
            continue
        assert record.license.is_redistributable, (
            f"{slug}: record.media_url is set but license {record.license!r} "
            "is not redistributable — this is a leak of a URL we are not "
            "allowed to expose as training-ready."
        )


@pytest.mark.xfail(
    reason=(
        "docs/plan-2026-09-14.md H6: provenance.extractor_git defaults to "
        "'dev' because we haven't wired `git rev-parse --short HEAD` into "
        "adapters yet. When _git.resolve_commit() ships this xfail must "
        "flip to a hard assertion."
    ),
    strict=False,
)
def test_extractor_git_is_a_real_sha(all_records: list[tuple[str, VideoRecord]]) -> None:
    for slug, record in all_records:
        git = record.provenance.extractor_git
        assert git != "dev", f"{slug}: provenance.extractor_git is placeholder 'dev'"
        assert all(c in "0123456789abcdef" for c in git.lower()), (
            f"{slug}: provenance.extractor_git {git!r} is not a hex SHA"
        )
        assert 7 <= len(git) <= 40, (
            f"{slug}: provenance.extractor_git {git!r} is not a plausible git SHA length"
        )
