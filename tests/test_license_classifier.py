"""Parametric tests for per-adapter license classifiers.

Each adapter has its own micro-classifier for license strings/URLs. A
mis-classification here silently poisons every downstream training
corpus, so these need broad coverage.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url
from specint.sources.peertube import _peertube_license
from specint.sources.wikimedia import _coerce_license


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("CC BY 4.0", License.CC_BY),
        ("CC-BY-4.0", License.CC_BY),
        ("CC BY-SA 3.0", License.CC_BY_SA),
        ("CCBYSA", License.CC_BY_SA),
        ("CC0", License.CC0),
        ("CC0 1.0", License.CC0),
        ("Public domain", License.PUBLIC_DOMAIN),
        ("PD", License.PUBLIC_DOMAIN),
        ("CC BY-NC 4.0", License.RESTRICTED),
        ("CC BY-ND 4.0", License.RESTRICTED),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
        ("random garbage", License.UNKNOWN),
    ],
)
def test_wikimedia_license_classifier(value, expected):
    assert _coerce_license(value) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
        ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
        ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
        ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_archive_license_classifier(url, expected):
    assert _license_from_url(url) is expected


@pytest.mark.parametrize(
    ("licence_id", "expected"),
    [
        (1, License.CC_BY),
        (2, License.CC_BY_SA),
        (7, License.CC0),
        (3, License.UNKNOWN),
        (4, License.UNKNOWN),
        (5, License.UNKNOWN),
        (6, License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_peertube_license_classifier(licence_id, expected):
    assert _peertube_license(licence_id) is expected
