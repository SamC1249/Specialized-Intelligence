"""Shared, conservative license classification.

Adapters should call `classify(*candidates)` with every string they have
that *might* declare a license — a MediaWiki `LicenseShortName`, an
Internet Archive `licenseurl`, a PeerTube `licence.name`, a page-level
`<link rel="license">` href, and so on. The function returns the
tightest `License` value we can *safely* conclude.

Design contract:

- **Fail closed.** Ambiguous or contradictory input returns
  `License.UNKNOWN`, never a redistributable license. Any adapter that
  emits `media_url` must gate on `License.is_redistributable`, so a
  wrong `UNKNOWN` only hurts yield; a wrong `CC_BY` corrupts the corpus.
- **Any non-commercial or no-derivatives signal wins.** If *any*
  candidate contains an NC/ND marker, we return `License.RESTRICTED`,
  even when another candidate looks like plain CC-BY. This handles the
  common upstream bug where the short label is truncated to "CC-BY" but
  the URL says "by-nc-sa".
- **Pure function.** No I/O, no regex compilation on the hot path
  (patterns are module-level constants), no logging.

The tests in `tests/test_license_utils.py` are the single source of
truth for behavior; when in doubt, extend the fixture list there.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from specint.records import License


def _normalize(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return ""
    stripped = unicodedata.normalize("NFKC", value).strip().lower()
    return re.sub(r"[\s_]+", " ", stripped)


_RESTRICTED_MARKERS: tuple[str, ...] = (
    "by-nc",
    "by nc",
    "byNC".lower(),
    "noncommercial",
    "non commercial",
    "non-commercial",
    "by-nd",
    "by nd",
    "noderiv",
    "no deriv",
    "no-deriv",
    "sampling+",
    "all rights reserved",
    "copyright",
    "proprietary",
)


_CC0_MARKERS: tuple[str, ...] = (
    "cc0",
    "cc-0",
    "publicdomain/zero",
    "public domain dedication",
    "zero universal",
)

_PD_MARKERS: tuple[str, ...] = (
    "public domain",
    "publicdomain",
    "pd-us",
    "pd-old",
    "us-gov",
    "pre-1928",
    "expired copyright",
)

_BY_SA_MARKERS: tuple[str, ...] = (
    "by-sa",
    "by sa",
    "sharealike",
    "share alike",
    "share-alike",
    "attribution-sharealike",
    "attribution share alike",
)

_BY_MARKERS: tuple[str, ...] = (
    "cc-by",
    "cc by",
    "ccby",
    "creativecommons.org/licenses/by/",
    "creative commons attribution",
    "attribution 4.0",
    "attribution 3.0",
    "attribution 2.0",
    "attribution 2.5",
    "attribution 1.0",
)

_OTHER_FREE_MARKERS: tuple[str, ...] = (
    "wtfpl",
    "unlicense",
    "cc-pdm",
    "art libre",
    "free art license",
)


def _has(any_of: tuple[str, ...], text: str) -> bool:
    return any(marker in text for marker in any_of)


def classify(*candidates: str | None) -> License:
    """Return the tightest safe `License` inferred from candidate strings.

    Semantics:

    - If **any** candidate carries a restricted marker (NC / ND / ARR /
      proprietary / copyright), return `License.RESTRICTED`.
    - Otherwise, take the most specific positive marker across
      candidates in the order CC0 > PD > CC-BY-SA > CC-BY > OTHER_FREE.
    - Otherwise, return `License.UNKNOWN`.
    """
    joined = " ".join(_normalize(c) for c in candidates if c).strip()
    if not joined:
        return License.UNKNOWN

    if _has(_RESTRICTED_MARKERS, joined):
        return License.RESTRICTED

    if _has(_CC0_MARKERS, joined):
        return License.CC0
    if _has(_PD_MARKERS, joined):
        return License.PUBLIC_DOMAIN
    if _has(_BY_SA_MARKERS, joined):
        return License.CC_BY_SA
    if _has(_BY_MARKERS, joined):
        return License.CC_BY
    if _has(_OTHER_FREE_MARKERS, joined):
        return License.OTHER_FREE
    return License.UNKNOWN


def classify_all(candidates: Iterable[str | None]) -> License:
    return classify(*candidates)


__all__ = ["classify", "classify_all"]
