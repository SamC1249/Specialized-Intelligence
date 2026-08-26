"""Adversarial matrix for the unified license classifier.

Adds W5's ≥30 real-world license strings across CC / PD / restricted /
unknown, so a future refactor that silently degrades classification
fails deterministically. Every case cites the source we've actually
seen it emitted from in the wild.
"""

from __future__ import annotations

import pytest

from specint.licenses import classify
from specint.records import License

CASES: list[tuple[str | None, str | None, License]] = [
    ("CC BY-SA 4.0", None, License.CC_BY_SA),
    ("Creative Commons Attribution-ShareAlike 4.0 International", None, License.CC_BY_SA),
    ("cc-by-sa-3.0", None, License.CC_BY_SA),
    ("CCBYSA", None, License.CC_BY_SA),
    (None, "https://creativecommons.org/licenses/by-sa/4.0/", License.CC_BY_SA),
    (None, "https://creativecommons.org/licenses/by-sa/2.5", License.CC_BY_SA),
    ("CC BY 4.0", None, License.CC_BY),
    ("Creative Commons Attribution 3.0 Unported", None, License.CC_BY),
    ("cc-by-4.0", None, License.CC_BY),
    ("CCBY", None, License.CC_BY),
    (None, "https://creativecommons.org/licenses/by/4.0/", License.CC_BY),
    (None, "https://creativecommons.org/licenses/by/2.0", License.CC_BY),
    ("CC0 1.0 Universal", None, License.CC0),
    ("cc0-1.0", None, License.CC0),
    ("CC0", None, License.CC0),
    ("No Rights Reserved", None, License.CC0),
    (None, "https://creativecommons.org/publicdomain/zero/1.0/", License.CC0),
    ("Public Domain", None, License.PUBLIC_DOMAIN),
    ("Public Domain Mark 1.0", None, License.PUBLIC_DOMAIN),
    ("PDM-1.0", None, License.PUBLIC_DOMAIN),
    ("United States Government Work", None, License.PUBLIC_DOMAIN),
    (None, "https://creativecommons.org/publicdomain/mark/1.0/", License.PUBLIC_DOMAIN),
    ("CC BY-NC 4.0", None, License.RESTRICTED),
    ("Attribution-NonCommercial-ShareAlike 4.0 International", None, License.RESTRICTED),
    ("CC BY-NC-ND 4.0", None, License.RESTRICTED),
    ("CC BY-ND 3.0", None, License.RESTRICTED),
    (None, "https://creativecommons.org/licenses/by-nc/4.0/", License.RESTRICTED),
    (None, "https://creativecommons.org/licenses/by-nc-sa/2.0/", License.RESTRICTED),
    (None, "https://creativecommons.org/licenses/by-nd/4.0/", License.RESTRICTED),
    ("All Rights Reserved", None, License.UNKNOWN),
    ("Proprietary", None, License.UNKNOWN),
    (None, None, License.UNKNOWN),
    ("", "", License.UNKNOWN),
    ("License unknown", None, License.UNKNOWN),
]


@pytest.mark.parametrize(("text", "url", "expected"), CASES)
def test_classify_matrix(text: str | None, url: str | None, expected: License) -> None:
    assert classify(text, url) is expected


def test_classify_prefers_restricted_over_by() -> None:
    """CC-BY-NC contains 'by' but must never classify as CC_BY."""
    assert classify("CC BY-NC 4.0") is License.RESTRICTED
    assert classify("Attribution NonCommercial ShareAlike") is License.RESTRICTED


def test_classify_url_and_text_agree() -> None:
    """If text and url both point at CC-BY-SA, still CC-BY-SA."""
    got = classify("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/")
    assert got is License.CC_BY_SA
