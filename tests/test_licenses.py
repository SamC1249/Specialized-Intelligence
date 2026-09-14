"""Contract tests for the central license classifier."""

from __future__ import annotations

import pytest

from specint.licenses import classify, classify_short_name, classify_url, combine
from specint.records import License


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
        ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
        ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
        ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
        ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nc-sa/4.0/", License.RESTRICTED),
        ("https://example.com/all-rights-reserved", License.RESTRICTED),
        ("CC BY-SA 4.0", License.CC_BY_SA),
        ("CC0", License.CC0),
        ("PD-US-Gov", License.PUBLIC_DOMAIN),
        ("Attribution 4.0", License.CC_BY),
        (None, License.UNKNOWN),
        ("", License.UNKNOWN),
        ("some string that means nothing", License.UNKNOWN),
    ],
)
def test_classify_covers_common_shapes(value: str | None, expected: License) -> None:
    assert classify(value) is expected


def test_aliases_match_classify() -> None:
    for v in (
        "https://creativecommons.org/licenses/by/4.0/",
        "CC-BY-SA",
        None,
    ):
        assert classify_url(v) == classify(v) == classify_short_name(v)


def test_by_nc_never_promotes_to_by() -> None:
    """A CC-BY-NC URL literally contains 'BY' — this must never fool us."""
    assert classify("cc-by-nc") is License.RESTRICTED
    assert classify("CC BY-NC 4.0") is License.RESTRICTED


def test_combine_least_privilege() -> None:
    assert combine(License.CC_BY, License.CC_BY) is License.CC_BY
    assert combine(License.CC_BY, License.RESTRICTED) is License.RESTRICTED
    assert combine(License.RESTRICTED, License.CC0) is License.RESTRICTED
    assert combine(License.UNKNOWN, License.CC_BY) is License.UNKNOWN
    assert combine(License.CC0, License.CC_BY) is License.CC0
    assert combine(License.CC_BY_SA, License.CC0) is License.CC_BY_SA
    assert combine(License.CC_BY, License.UNKNOWN) is License.CC_BY
