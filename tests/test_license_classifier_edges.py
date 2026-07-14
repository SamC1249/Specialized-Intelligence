"""Adversarial license-classifier edge cases.

Locks in the current classifier truth-table for every source that ships
a license normalizer. If Coding-Agent refactors any of these normalizers,
the tests must be updated *deliberately*, not accidentally.

The hard invariant: any CC-BY-NC, CC-BY-ND, or CC-BY-NC-SA variant must
classify as `License.RESTRICTED` — never as CC-BY or CC-BY-SA. A false
positive here would silently mislabel a non-redistributable video as
training-clean.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url as archive_license
from specint.sources.wikimedia import _coerce_license as wikimedia_license

WIKIMEDIA_CASES: list[tuple[str, License]] = [
    ("cc0", License.CC0),
    ("CC0 1.0 Universal", License.CC0),
    ("CC-BY-SA 4.0", License.CC_BY_SA),
    ("cc-by-sa-3.0", License.CC_BY_SA),
    ("CC BY-SA 4.0", License.CC_BY_SA),
    ("CC-BY 4.0", License.CC_BY),
    ("CC BY 3.0", License.CC_BY),
    ("Public Domain", License.PUBLIC_DOMAIN),
    ("PD", License.PUBLIC_DOMAIN),
    ("CC-BY-NC 4.0", License.RESTRICTED),
    ("CC BY-NC 4.0", License.RESTRICTED),
    ("cc-by-nc-sa-4.0", License.RESTRICTED),
    ("CC-BY-ND 3.0", License.RESTRICTED),
    ("cc-by-nc-nd-2.5", License.RESTRICTED),
    ("   CC-BY-SA 4.0   ", License.CC_BY_SA),
    ("", License.UNKNOWN),
    ("some free license we don't recognise", License.UNKNOWN),
]


@pytest.mark.parametrize("raw, expected", WIKIMEDIA_CASES)
def test_wikimedia_license_classifier(raw: str, expected: License) -> None:
    assert wikimedia_license(raw) is expected, f"wikimedia({raw!r}) misclassified"


ARCHIVE_URL_CASES: list[tuple[str, License]] = [
    ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
    ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
    ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
    ("https://creativecommons.org/licenses/by/3.0/", License.CC_BY),
    ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
    ("https://creativecommons.org/licenses/by-sa/3.0/", License.CC_BY_SA),
    ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nc-sa/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nc-nd/4.0/", License.RESTRICTED),
    ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
    ("https://example.test/custom-license", License.UNKNOWN),
    ("", License.UNKNOWN),
]


@pytest.mark.parametrize("url, expected", ARCHIVE_URL_CASES)
def test_archive_license_from_url(url: str, expected: License) -> None:
    assert archive_license(url) is expected, f"archive_org({url!r}) misclassified"


def test_no_nc_or_nd_ever_maps_to_redistributable() -> None:
    """Bright-line safety net across both classifiers.

    Any string containing an NC or ND marker MUST NOT return an enum
    for which `is_redistributable` is True.
    """
    nc_nd_probes = [
        "CC-BY-NC 4.0",
        "CC BY-NC 4.0",
        "cc-by-nc-sa-4.0",
        "cc-by-nc-nd-2.5",
        "CC-BY-ND 3.0",
        "https://creativecommons.org/licenses/by-nc/4.0/",
        "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "https://creativecommons.org/licenses/by-nd/4.0/",
    ]
    for probe in nc_nd_probes:
        w = wikimedia_license(probe)
        a = archive_license(probe)
        assert not w.is_redistributable, (
            f"wikimedia classified {probe!r} as redistributable {w!r} — legal risk"
        )
        assert not a.is_redistributable, (
            f"archive_org classified {probe!r} as redistributable {a!r} — legal risk"
        )
