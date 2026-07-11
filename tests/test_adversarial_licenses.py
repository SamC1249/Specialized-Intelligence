"""Adversarial license classification tests.

If any source adapter ever regresses and classifies a CC-BY-NC or
CC-BY-ND record as *redistributable*, we will silently poison our
training corpus. These tests force the four current adapters through
CC-BY-NC / CC-BY-ND fixtures and assert both:

  - the classified ``license`` field is ``License.RESTRICTED``, and
  - ``media_url`` is ``None`` (never leak a media URL for a
    non-redistributable record).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource
from specint.sources.wikimedia import WikimediaCommonsSource

QUERY = SourceQuery(terms=["cooking"], max_results=25)


def test_wikimedia_rejects_nc_and_nd(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "wikimedia/search_adversarial_licenses.json").read_text())
    records = WikimediaCommonsSource().parse(raw, QUERY)
    by_id = {r.source_native_id: r for r in records}

    nc = by_id["20001"]
    assert nc.license is License.RESTRICTED, "CC-BY-NC must map to RESTRICTED"
    assert nc.media_url is None, "RESTRICTED records must never leak a media URL"

    nd = by_id["20002"]
    assert nd.license is License.RESTRICTED, "CC-BY-ND must map to RESTRICTED"
    assert nd.media_url is None

    trailer = by_id["20003"]
    assert trailer.license is License.CC_BY, "CC-BY is still license-clean"


def test_archive_org_rejects_nc_and_nd(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "archive_org/search_adversarial_licenses.json").read_text())
    records = ArchiveOrgSource().parse(raw, QUERY)
    by_id = {r.source_native_id: r for r in records}

    nc = by_id["NCTeaser2025"]
    assert nc.license is License.RESTRICTED
    assert nc.media_url is None

    nd = by_id["NDCompilation2024"]
    assert nd.license is License.RESTRICTED
    assert nd.media_url is None

    mystery = by_id["MysteryLicense"]
    assert mystery.license is License.UNKNOWN
    assert mystery.media_url is None


@pytest.mark.parametrize(
    "short_name",
    [
        "CC BY-NC 4.0",
        "CC BY-NC-SA 4.0",
        "CC BY-ND 4.0",
        "CC BY-NC-ND 4.0",
    ],
)
def test_wikimedia_license_regex_rejects_nc_nd_variants(short_name: str):
    from specint.sources.wikimedia import _coerce_license

    assert _coerce_license(short_name) is License.RESTRICTED


@pytest.mark.parametrize(
    "license_url",
    [
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    ],
)
def test_archive_org_license_regex_rejects_nc_nd_variants(license_url: str):
    from specint.sources.archive_org import _license_from_url

    assert _license_from_url(license_url) is License.RESTRICTED
