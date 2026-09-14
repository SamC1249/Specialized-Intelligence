"""Central license classification.

Every adapter and page-level heuristic must funnel through
`classify_url` / `classify_short_name` / `classify_meta`, so that a
change in policy (e.g. treating a new SPDX identifier as clean) needs
edits in exactly one file.

Rules (deliberately conservative — we default to `UNKNOWN`):

  * Any URL or short-name matching *any* of the `RESTRICTED` markers
    (`-NC-`, `-ND-`, "no derivatives", "non commercial", etc.) resolves
    to `RESTRICTED` even if it also mentions "BY".
  * We only promote to `CC_BY` / `CC_BY_SA` / `CC0` / `PUBLIC_DOMAIN`
    if the string contains an unambiguous signal.
  * Otherwise `UNKNOWN` — never `redistributable` by default.

The classifier is intentionally string-based (no URL parsing) so it
works on hand-typed metadata fields (`extmetadata.LicenseShortName`,
`<meta name="license">`, etc.) as well as canonical URLs.
"""

from __future__ import annotations

from specint.records import License

_RESTRICTED_MARKERS: tuple[str, ...] = (
    "-nc-",
    "-nd-",
    "/nc/",
    "/nd/",
    "by-nc",
    "bync",
    "by-nd",
    "bynd",
    "noncommercial",
    "non-commercial",
    "no-derivatives",
    "noderivatives",
    "no-derivs",
    "noderivs",
    "all rights reserved",
    "all-rights-reserved",
    "allrightsreserved",
    "copyrighted",
    "proprietary",
)

_CC0_MARKERS: tuple[str, ...] = (
    "cc0",
    "publicdomain/zero",
    "creativecommons.org/publicdomain/zero",
)

_PD_MARKERS: tuple[str, ...] = (
    "publicdomain",
    "public-domain",
    "public domain",
    "pd-us",
    "pd-usgov",
    "wikimedia commons pd",
)

_BY_SA_MARKERS: tuple[str, ...] = (
    "by-sa",
    "bysa",
    "share-alike",
    "sharealike",
    "attribution-sharealike",
    "attribution share alike",
    "creativecommons.org/licenses/by-sa",
)

_BY_MARKERS: tuple[str, ...] = (
    "creativecommons.org/licenses/by/",
    "licenses/by/",
    "cc by",
    "cc-by",
    "ccby",
    "attribution 4.0",
    "attribution 3.0",
    "attribution 2.0",
    "attribution-only",
)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def _has_any(needle: str, markers: tuple[str, ...]) -> bool:
    return any(m in needle for m in markers)


def classify(value: str | None) -> License:
    """Classify a free-form license string (URL, SPDX short-name, badge text)."""
    s = _normalize(value)
    if not s:
        return License.UNKNOWN

    if _has_any(s, _RESTRICTED_MARKERS):
        return License.RESTRICTED

    if _has_any(s, _CC0_MARKERS):
        return License.CC0

    if _has_any(s, _BY_SA_MARKERS):
        return License.CC_BY_SA

    if _has_any(s, _BY_MARKERS):
        return License.CC_BY

    if _has_any(s, _PD_MARKERS):
        return License.PUBLIC_DOMAIN

    return License.UNKNOWN


def classify_url(url: str | None) -> License:
    """Alias — kept for call-site readability."""
    return classify(url)


def classify_short_name(short_name: str | None) -> License:
    """Alias — kept for call-site readability."""
    return classify(short_name)


def combine(page: License, embedded: License) -> License:
    """Resolve conflict between a page-level license and a record-level one.

    Common Crawl JSON-LD `VideoObject` blocks frequently lie about a
    contentUrl's license. The *page* license (rel=license / meta) is
    authoritative:

      * If either side is `RESTRICTED`, the answer is `RESTRICTED`
        (rule of least privilege — an embedded video that claims a
        permissive license inside an all-rights-reserved page is still
        untrustworthy).
      * Otherwise return the page license verbatim; the embedded
        license is treated as unverified metadata.
    """
    if License.RESTRICTED in (page, embedded):
        return License.RESTRICTED
    return page
