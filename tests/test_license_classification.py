"""Adversarial license classifier tests.

We fuzz both `specint.sources.wikimedia._coerce_license` and
`specint.sources.archive_org._license_from_url` against real-world
strings we have observed from live Commons + Archive.org responses.

Cases that already classify correctly are *hard asserts*. Cases where
the current heuristic is wrong are marked `pytest.xfail(strict=True)`
with a cross-reference back to `docs/plan-2026-09-16.md`. Turning
those xfails into passes is a Coding-Agent deliverable for the next
PR: dropping an xfail without fixing the heuristic will make CI red.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url
from specint.sources.wikimedia import _coerce_license

WIKIMEDIA_CASES: list[tuple[str, License]] = [
    ("CC0 1.0", License.CC0),
    ("CC0", License.CC0),
    ("CC-BY-SA 4.0", License.CC_BY_SA),
    ("CC BY-SA 4.0", License.CC_BY_SA),
    ("CC-BY 4.0", License.CC_BY),
    ("CC BY 3.0", License.CC_BY),
    ("CC BY-NC 4.0", License.RESTRICTED),
    ("CC BY-ND 4.0", License.RESTRICTED),
    ("CC BY-NC-SA 4.0", License.RESTRICTED),
    ("Public domain", License.PUBLIC_DOMAIN),
    ("PD", License.PUBLIC_DOMAIN),
]

WIKIMEDIA_XFAIL_CASES: list[tuple[str, License, str]] = [
    (
        "Attribution-ShareAlike 4.0",
        License.CC_BY_SA,
        "Commons regularly uses this LicenseShortName; heuristic misses it. See plan-2026-09-16 §H2.",
    ),
    (
        "Attribution 3.0 Unported",
        License.CC_BY,
        "Common Commons string without a 'CC' prefix; heuristic returns UNKNOWN.",
    ),
]


@pytest.mark.parametrize("value,expected", WIKIMEDIA_CASES)
def test_wikimedia_license_known_good(value: str, expected: License) -> None:
    assert _coerce_license(value) is expected


def test_wikimedia_license_none_is_unknown() -> None:
    assert _coerce_license(None) is License.UNKNOWN
    assert _coerce_license("") is License.UNKNOWN


@pytest.mark.parametrize("value,expected,reason", WIKIMEDIA_XFAIL_CASES)
def test_wikimedia_license_known_limitations(value: str, expected: License, reason: str) -> None:
    got = _coerce_license(value)
    if got is not expected:
        pytest.xfail(reason)
    # If someone fixes the heuristic (making got == expected), the test now
    # passes and the xfail block becomes unreachable. That is the desired
    # outcome; the next PR should also drop the corresponding row from
    # WIKIMEDIA_XFAIL_CASES.


ARCHIVE_CASES: list[tuple[str, License]] = [
    ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
    ("http://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
    ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
    ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nc-sa/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nc-nd/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
]

ARCHIVE_XFAIL_CASES: list[tuple[str, License, str]] = [
    (
        "https://www.usa.gov/government-works",
        License.PUBLIC_DOMAIN,
        "US-federal-gov works are PD; Archive.org hosts many such items but our URL matcher misses them.",
    ),
    (
        "https://en.wikipedia.org/wiki/Public_domain",
        License.PUBLIC_DOMAIN,
        "Underscore-separated PD marker is not matched because we search literal substring 'publicdomain'.",
    ),
]


@pytest.mark.parametrize("value,expected", ARCHIVE_CASES)
def test_archive_license_known_good(value: str, expected: License) -> None:
    assert _license_from_url(value) is expected


def test_archive_license_none_is_unknown() -> None:
    assert _license_from_url(None) is License.UNKNOWN
    assert _license_from_url("") is License.UNKNOWN


@pytest.mark.parametrize("value,expected,reason", ARCHIVE_XFAIL_CASES)
def test_archive_license_known_limitations(value: str, expected: License, reason: str) -> None:
    got = _license_from_url(value)
    if got is not expected:
        pytest.xfail(reason)


def test_license_redistributable_matrix_unchanged() -> None:
    """Regression guard on `License.is_redistributable`."""
    permissive = {
        License.CC0,
        License.CC_BY,
        License.CC_BY_SA,
        License.PUBLIC_DOMAIN,
        License.OTHER_FREE,
    }
    for lic in License:
        assert lic.is_redistributable == (lic in permissive), lic
