"""Adversarial license-classification test suite.

Bugs here mean *training on non-redistributable content*. Every case
below is either something we saw in the wild while inspecting sample
API payloads, or a plausible variation that a reviewer should insist
on. When adding a new source adapter, add its own adversarial cases to
this file and reuse the parametric shape.
"""

from __future__ import annotations

import pytest

from specint.records import License
from specint.sources.archive_org import _license_from_url as archive_org_from_url
from specint.sources.europeana import _license_from_rights as europeana_from_rights
from specint.sources.wikimedia import _coerce_license as wikimedia_from_shortname


@pytest.mark.parametrize(
    "short_name,expected",
    [
        # canonical CC values
        ("CC0", License.CC0),
        ("CC0 1.0 Universal", License.CC0),
        ("CC BY 4.0", License.CC_BY),
        ("CC BY-SA 4.0", License.CC_BY_SA),
        # NC / ND must NEVER end up in a redistributable tier
        ("CC BY-NC 4.0", License.RESTRICTED),
        ("CC BY-NC-SA 4.0", License.RESTRICTED),
        ("CC BY-NC-ND 4.0", License.RESTRICTED),
        ("CC BY-ND 4.0", License.RESTRICTED),
        # long-form Commons strings (Wikimedia sometimes emits these)
        ("Attribution-ShareAlike 3.0 Unported", License.CC_BY_SA),
        ("Attribution 4.0 International", License.CC_BY),
        # public domain / PDM
        ("Public domain", License.PUBLIC_DOMAIN),
        ("PDM 1.0", License.PUBLIC_DOMAIN),
        ("Public Domain Mark 1.0", License.PUBLIC_DOMAIN),
        # nothing / unknown must default to UNKNOWN, never a free tier
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
        ("All rights reserved", License.UNKNOWN),
        ("Proprietary", License.UNKNOWN),
    ],
)
def test_wikimedia_short_name_license_classifier(short_name, expected):
    assert wikimedia_from_shortname(short_name) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
        ("https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
        ("https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/licenses/by-nc-sa/4.0/", License.RESTRICTED),
        ("https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
        ("https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
        ("http://rightsstatements.org/vocab/InC/1.0/", License.UNKNOWN),
        ("", License.UNKNOWN),
        (None, License.UNKNOWN),
    ],
)
def test_archive_org_license_url_classifier(url, expected):
    assert archive_org_from_url(url) is expected


@pytest.mark.parametrize(
    "rights,expected",
    [
        ("https://creativecommons.org/licenses/by-nc-sa/4.0/", License.RESTRICTED),
        (["http://creativecommons.org/publicdomain/mark/1.0/"], License.PUBLIC_DOMAIN),
        (
            [
                "http://rightsstatements.org/vocab/InC-EDU/1.0/",
                "http://creativecommons.org/licenses/by/4.0/",
            ],
            License.UNKNOWN,
        ),
        (None, License.UNKNOWN),
    ],
)
def test_europeana_rights_classifier(rights, expected):
    assert europeana_from_rights(rights) is expected
