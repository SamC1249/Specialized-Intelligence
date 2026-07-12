"""Adversarial tests for the shared license classifier.

These fixtures are the executable spec: if you change `classify()`
behaviour, the ONLY correct move is to add / update rows here first,
then patch the implementation.

The plan for the day (docs/plan-2026-07-12.md, H3) requires the
classifier to be **conservative**: any ambiguity must fall to UNKNOWN,
and *any* NC/ND signal in *any* candidate string wins across the whole
call. That's what these tests pin down.
"""

from __future__ import annotations

import pytest

from specint.quality.license_utils import classify, classify_all
from specint.records import License


@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        # Empty / null inputs → UNKNOWN
        ((), License.UNKNOWN),
        ((None,), License.UNKNOWN),
        (("",), License.UNKNOWN),
        (("   ", None, ""), License.UNKNOWN),
        # Straightforward positive signals
        (("CC0",), License.CC0),
        (("cc-0",), License.CC0),
        (("https://creativecommons.org/publicdomain/zero/1.0/",), License.CC0),
        (("Public Domain",), License.PUBLIC_DOMAIN),
        (("us-gov",), License.PUBLIC_DOMAIN),
        (("CC-BY 4.0",), License.CC_BY),
        (("cc by 4.0",), License.CC_BY),
        (("Creative Commons Attribution 4.0 International",), License.CC_BY),
        (("https://creativecommons.org/licenses/by/4.0/",), License.CC_BY),
        (("CC-BY-SA 3.0",), License.CC_BY_SA),
        (("attribution share alike",), License.CC_BY_SA),
        (("WTFPL",), License.OTHER_FREE),
        (("Unlicense",), License.OTHER_FREE),
        # Restricted signals must win, even when a permissive marker is present
        (("CC-BY-NC 4.0",), License.RESTRICTED),
        (("CC-BY-ND",), License.RESTRICTED),
        (("Attribution-NonCommercial-ShareAlike 4.0",), License.RESTRICTED),
        (("All rights reserved",), License.RESTRICTED),
        (("Copyright 2024 Foo Corp",), License.RESTRICTED),
        # Cross-candidate: label says CC-BY but URL says by-nc → RESTRICTED
        (
            ("CC-BY", "https://creativecommons.org/licenses/by-nc/4.0/"),
            License.RESTRICTED,
        ),
        # Cross-candidate: partial data on one candidate, definitive on another
        ((None, "CC-BY-SA 4.0"), License.CC_BY_SA),
        (("", "public domain"), License.PUBLIC_DOMAIN),
        # Unicode + spacing weirdness must still classify
        (("CC\u2010BY\u20104.0",), License.UNKNOWN),  # unicode hyphens don't match ASCII patterns
        (("  CC  BY  4.0  ",), License.CC_BY),
        (("cc_by_sa_4.0",), License.CC_BY_SA),
        # Non-string junk → UNKNOWN
        ((123,), License.UNKNOWN),  # type: ignore[arg-type]
        ((object(),), License.UNKNOWN),  # type: ignore[arg-type]
    ],
)
def test_classify(candidates: tuple[object, ...], expected: License) -> None:
    assert classify(*candidates) == expected


def test_classify_all_wraps_classify() -> None:
    assert classify_all(["CC-BY 4.0", None]) is License.CC_BY


def test_classifier_never_upgrades_to_restricted_media() -> None:
    """If classify() returns anything but a redistributable license, callers
    must skip media redistribution. Guard here so the contract can't quietly
    drift."""
    for value in License:
        if value is License.UNKNOWN or value is License.RESTRICTED:
            assert not value.is_redistributable


def test_nc_marker_never_becomes_by() -> None:
    """The single most dangerous drift: a truncated 'CC-BY' label with an
    NC full URL must never resolve to CC_BY. Pin it independently of the
    parametrized cases so a future refactor cannot silently loosen this."""
    assert (
        classify("CC-BY", "https://creativecommons.org/licenses/by-nc/4.0/") is License.RESTRICTED
    )
    assert (
        classify(
            "Creative Commons Attribution 4.0 International",
            "https://example.org/licenses/by-nd/4.0/",
        )
        is License.RESTRICTED
    )
