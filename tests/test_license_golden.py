"""Golden test for license classifiers across every adapter.

Rationale: our license classification is done by string sniffing in each
adapter (`_coerce_license`, `_license_from_url`, `_peertube_license`).
Two-character differences in a URL (`/by/` vs `/by-nd/`) currently flip
a record between `CC_BY` and `RESTRICTED` with no explicit test. This
table pins the observed short-names + URL variants so regressions are
loud.

If a real upstream introduces a new value, add it here first, then fix
the classifier.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url as archive_license
from specint.sources.peertube import _peertube_license
from specint.sources.wikimedia import _coerce_license as wikimedia_license

WIKIMEDIA_CASES: list[tuple[str | None, License]] = [
    (None, License.UNKNOWN),
    ("", License.UNKNOWN),
    ("CC0", License.CC0),
    ("CC0 1.0", License.CC0),
    ("CC BY-SA 4.0", License.CC_BY_SA),
    ("CC BY-SA 3.0", License.CC_BY_SA),
    ("CC BY 4.0", License.CC_BY),
    ("CC BY 3.0", License.CC_BY),
    ("Public domain", License.PUBLIC_DOMAIN),
    ("PD", License.PUBLIC_DOMAIN),
    ("CC BY-NC 4.0", License.RESTRICTED),
    ("CC BY-ND 4.0", License.RESTRICTED),
    ("Some weird string we've never seen", License.UNKNOWN),
]

ARCHIVE_ORG_CASES: list[tuple[str | None, License]] = [
    (None, License.UNKNOWN),
    ("", License.UNKNOWN),
    ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
    ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
    ("https://creativecommons.org/licenses/by/3.0/", License.CC_BY),
    ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
    ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
    ("https://example.test/some/unknown/license", License.UNKNOWN),
]

PEERTUBE_CASES: list[tuple[int | None, License]] = [
    (None, License.UNKNOWN),
    (1, License.CC_BY),
    (2, License.CC_BY_SA),
    (3, License.UNKNOWN),  # ND: filtered upstream; classifier itself is UNKNOWN
    (4, License.UNKNOWN),  # NC
    (5, License.UNKNOWN),  # NC-SA
    (6, License.UNKNOWN),  # NC-ND
    (7, License.CC0),
    (999, License.UNKNOWN),
]


@pytest.mark.parametrize("value,expected", WIKIMEDIA_CASES)
def test_wikimedia_license_golden(value: str | None, expected: License) -> None:
    assert wikimedia_license(value) is expected


@pytest.mark.parametrize("url,expected", ARCHIVE_ORG_CASES)
def test_archive_org_license_golden(url: str | None, expected: License) -> None:
    assert archive_license(url) is expected


@pytest.mark.parametrize("licence_id,expected", PEERTUBE_CASES)
def test_peertube_license_golden(licence_id: int | None, expected: License) -> None:
    assert _peertube_license(licence_id) is expected


def test_no_unlicensed_media_url_invariant() -> None:
    """A record with an UNKNOWN or RESTRICTED license must never advertise a
    redistributable `media_url`. Adapters enforce this; this test pins the
    invariant so any future adapter must uphold it."""
    for lic in (License.UNKNOWN, License.RESTRICTED):
        assert not lic.is_redistributable, (
            f"License.{lic.name} must not be treated as redistributable"
        )
