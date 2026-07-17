"""Unit tests for the unified license classifier."""

from __future__ import annotations

import pytest

from specint.licenses import LicenseVerdict, classify
from specint.records import License


@pytest.mark.parametrize(
    "url, short, expected",
    [
        ("https://creativecommons.org/publicdomain/zero/1.0/", "CC0", License.CC0),
        ("https://creativecommons.org/licenses/by/4.0/", "CC BY 4.0", License.CC_BY),
        ("https://creativecommons.org/licenses/by-sa/3.0/", "CC BY-SA", License.CC_BY_SA),
        ("https://creativecommons.org/licenses/by-nc/4.0/", "CC BY-NC", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nc-sa/4.0/", "by-nc-sa", License.RESTRICTED),
        ("https://creativecommons.org/publicdomain/mark/1.0/", "PDM", License.PUBLIC_DOMAIN),
        (None, "cc0", License.CC0),
        (None, "public domain", License.PUBLIC_DOMAIN),
        (None, "No known copyright restrictions", License.PUBLIC_DOMAIN),
        (None, None, License.UNKNOWN),
        ("https://example.com/nothing", None, License.UNKNOWN),
    ],
)
def test_classify_expected_labels(url, short, expected):
    verdict = classify(url=url, short_name=short)
    assert verdict.license is expected


def test_classify_high_confidence_when_both_agree():
    v = classify(
        url="https://creativecommons.org/licenses/by-sa/4.0/",
        short_name="CC BY-SA 4.0",
    )
    assert v.license is License.CC_BY_SA
    assert v.confidence >= 0.90


def test_classify_marks_restricted_wins_over_open():
    v = classify(
        url="https://creativecommons.org/licenses/by-nc/4.0/",
        short_name="CC BY 4.0",
    )
    assert v.license is License.RESTRICTED


def test_classify_unknown_has_zero_confidence():
    v = classify(url=None, short_name=None)
    assert v.license is License.UNKNOWN
    assert v.confidence == 0.0
    assert not v.is_redistributable
    assert not v.strict_ok()


def test_verdict_is_frozen_dataclass():
    from dataclasses import FrozenInstanceError

    v = LicenseVerdict(License.CC0, 0.95)
    with pytest.raises(FrozenInstanceError):
        v.confidence = 0.1  # type: ignore[misc]


def test_strict_ok_threshold_behavior():
    v = classify(url="https://creativecommons.org/licenses/by/4.0/")
    assert v.strict_ok(0.5)
    v_low = LicenseVerdict(License.CC_BY, 0.3)
    assert not v_low.strict_ok(0.5)
