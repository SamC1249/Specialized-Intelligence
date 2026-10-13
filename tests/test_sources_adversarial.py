"""Adversarial fixture tests.

Addresses Priority-A deliverable in `docs/plan-2026-10-12.md`:
"one failing-license and one malformed-payload fixture per source … assert
exclusion / graceful degradation."

Each source gets:
  * `adversarial_*`: well-formed payloads that *should be rejected or
    attenuated* (ND/NC license, audio-only files mislabelled by title,
    missing identifiers, no VideoObject, mixed `@type` arrays).
  * `malformed_*`: structurally busted payloads that must degrade to an
    empty list without raising.
"""

from __future__ import annotations

from pathlib import Path

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.common_crawl import CommonCrawlRecipeSource
from specint.sources.peertube import PeerTubeSource
from specint.sources.wikimedia import WikimediaCommonsSource

_QUERY = SourceQuery(terms=["adversarial"], max_results=10)


def _load_json(fixtures_dir: Path, rel: str):
    import json

    return json.loads((fixtures_dir / rel).read_text())


def _load_text(fixtures_dir: Path, rel: str) -> str:
    return (fixtures_dir / rel).read_text()


# ---------------------------- Wikimedia ----------------------------


def test_wikimedia_rejects_nc_and_audio_and_degrades(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "wikimedia/adversarial_search.json")
    records = WikimediaCommonsSource().parse(raw, _QUERY)
    titles = {r.title for r in records}

    # Audio-mimed file with a .ogv title must be filtered out on MIME.
    assert "File:Chef_interview.ogv" not in titles
    # Missing imageinfo must be skipped.
    assert "File:Broken_page.webm" not in titles

    # NC still produces a record, but as RESTRICTED and without media_url.
    nc = next((r for r in records if r.title == "File:Non_commercial_soup.webm"), None)
    assert nc is not None
    assert nc.license is License.RESTRICTED
    assert nc.media_url is None

    # Unknown license short-name must land in UNKNOWN and withhold media.
    mystery = next((r for r in records if r.title == "File:Mystery_license.webm"), None)
    assert mystery is not None
    assert mystery.license is License.UNKNOWN
    assert mystery.media_url is None


def test_wikimedia_malformed_payload_returns_empty(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "wikimedia/malformed_search.json")
    assert WikimediaCommonsSource().parse(raw, _QUERY) == []


# ---------------------------- PeerTube ----------------------------


def test_peertube_rejects_nd_and_handles_missing_fields(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "peertube/adversarial_search.json")
    records = PeerTubeSource().parse(raw, _QUERY)
    titles = {r.title for r in records}

    # ND license must be excluded entirely.
    assert "No Derivatives Cake" not in titles
    # Missing uuid must be skipped.
    assert "Anonymous Omelette" not in titles

    # Missing account.host must fall back to the __instance__ hostname.
    pancakes = next((r for r in records if r.title == "Pancakes Without Host"), None)
    assert pancakes is not None
    assert "example.test" in str(pancakes.url)
    # Empty files list means no media_url even if license is clean.
    assert pancakes.media_url is None
    assert pancakes.license is License.CC0


def test_peertube_malformed_payload_returns_empty(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "peertube/malformed_search.json")
    assert PeerTubeSource().parse(raw, _QUERY) == []


# ---------------------------- Archive.org ----------------------------


def test_archive_rejects_nd_missing_id_and_garbage_runtime(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "archive_org/adversarial_search.json")
    records = ArchiveOrgSource().parse(raw, _QUERY)
    by_id = {r.source_native_id: r for r in records}

    # ND license is kept as RESTRICTED but media_url suppressed.
    nd = by_id.get("NoDerivsRecipe")
    assert nd is not None
    assert nd.license is License.RESTRICTED
    assert nd.media_url is None

    # Missing identifier must drop the row entirely.
    assert "Missing Identifier" not in {r.title for r in records}

    # Garbage runtime string must not raise and must leave duration_s None.
    garbage = by_id.get("GarbageRuntime")
    assert garbage is not None
    assert garbage.duration_s is None

    # No license at all → UNKNOWN, media_url suppressed.
    none = by_id.get("NoLicenseAtAll")
    assert none is not None
    assert none.license is License.UNKNOWN
    assert none.media_url is None


def test_archive_malformed_payload_returns_empty(fixtures_dir: Path) -> None:
    raw = _load_json(fixtures_dir, "archive_org/malformed_search.json")
    assert ArchiveOrgSource().parse(raw, _QUERY) == []


# ---------------------------- Common Crawl ----------------------------


def test_common_crawl_mixed_types_and_invalid_jsonld(fixtures_dir: Path) -> None:
    html = _load_text(fixtures_dir, "common_crawl/adversarial_page.html")
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://adversarial.test/page"}, _QUERY
    )
    assert len(records) == 1
    r = records[0]
    assert r.title == "Combo-Typed Video"
    assert r.duration_s == 195.0
    assert r.height == 720
    # Common Crawl adapter must never auto-trust an embedded license.
    assert r.license is License.UNKNOWN
    assert r.media_url is None


def test_common_crawl_no_jsonld_returns_empty(fixtures_dir: Path) -> None:
    html = _load_text(fixtures_dir, "common_crawl/malformed_page.html")
    records = CommonCrawlRecipeSource().parse(
        {"html": html, "url": "https://adversarial.test/plain"}, _QUERY
    )
    assert records == []


# ------------------- cross-source invariants -------------------


def test_no_intrasource_id_collisions_in_adversarial_bundle(fixtures_dir: Path) -> None:
    """Record IDs must be unique within a single adapter's output."""
    bundles = [
        (
            WikimediaCommonsSource(),
            _load_json(fixtures_dir, "wikimedia/adversarial_search.json"),
        ),
        (
            PeerTubeSource(),
            _load_json(fixtures_dir, "peertube/adversarial_search.json"),
        ),
        (
            ArchiveOrgSource(),
            _load_json(fixtures_dir, "archive_org/adversarial_search.json"),
        ),
    ]
    for src, raw in bundles:
        records = src.parse(raw, _QUERY)
        ids = [r.id for r in records]
        assert len(ids) == len(set(ids)), f"id collision in {src.slug}: {ids}"
