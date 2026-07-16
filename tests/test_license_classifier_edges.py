"""Adversarial license-classifier tests.

Pin down how each adapter's license coercion behaves on the fragile
edge cases the Adversarial-Agent 07-14 plan called out: whitespace
variants, NBSP, obscure CC-NC/ND/GFDL strings, and mixed-case URLs.
No adapter is allowed to *accidentally* promote a restricted license.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url
from specint.sources.common_crawl import _cc_license_from_url
from specint.sources.peertube import _peertube_license
from specint.sources.wikimedia import _coerce_license


@pytest.mark.parametrize(
    "value,expected",
    [
        ("CC0", License.CC0),
        ("CC0 1.0", License.CC0),
        ("CC BY 4.0", License.CC_BY),
        ("CC-BY 4.0", License.CC_BY),
        ("CC BY-SA 4.0", License.CC_BY_SA),
        ("Attribution-ShareAlike", License.CC_BY_SA),
        ("CC BY-NC 4.0", License.RESTRICTED),
        ("cc-by-nc-nd-2.5", License.RESTRICTED),
        ("Attribution-NonCommercial-ShareAlike 4.0 International", License.RESTRICTED),
        ("CC BY-ND 4.0", License.RESTRICTED),
        # NBSP variant of CC BY-NC 4.0
        ("CC\u00a0BY-NC\u00a04.0", License.RESTRICTED),
        ("Public Domain", License.PUBLIC_DOMAIN),
        ("PD", License.PUBLIC_DOMAIN),
        ("GFDL 1.2", License.UNKNOWN),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_wikimedia_coerce_license(value, expected):
    assert _coerce_license(value) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
        ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
        ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
        ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
        ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
        # Uppercase host, still matches
        ("https://CreativeCommons.org/licenses/by/4.0/", License.CC_BY),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_archive_org_license_from_url(url, expected):
    assert _license_from_url(url) is expected


@pytest.mark.parametrize(
    "licence_id,expected",
    [
        (1, License.CC_BY),
        (2, License.CC_BY_SA),
        (3, License.UNKNOWN),  # No Derivatives — filtered upstream, not our concern here
        (4, License.UNKNOWN),  # Non Commercial
        (5, License.UNKNOWN),
        (6, License.UNKNOWN),
        (7, License.CC0),
        (None, License.UNKNOWN),
    ],
)
def test_peertube_license_id_mapping(licence_id, expected):
    assert _peertube_license(licence_id) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
        ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
        ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
        ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
        ("https://random.example/license.html", License.UNKNOWN),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_common_crawl_license_url(url, expected):
    assert _cc_license_from_url(url) is expected
