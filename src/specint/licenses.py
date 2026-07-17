"""Unified license classification.

Each source adapter used to re-implement its own regex against license
URLs and short-name strings. That drifted: `by-nc-sa` was correctly
rejected on Archive.org but silently accepted on some Wikimedia
payloads because the check ordering differed. This module centralises
that logic and returns a `(License, confidence)` pair so downstream
code can filter on confidence, not just enum equality.

Confidence bands (documented, not learned):
  - 0.95 : both URL and short-name agree, or URL matches an explicit
           creativecommons.org / publicdomain path.
  - 0.80 : one of URL / short-name matches; the other is missing or
           ambiguous.
  - 0.50 : matches a heuristic keyword (e.g. "public domain" in a
           free-text field) with no URL.
  - 0.00 : `License.UNKNOWN` — do NOT use for training.

Callers that want a strict corpus should require `confidence >= 0.80`
AND `license.is_redistributable`.
"""

from __future__ import annotations

from dataclasses import dataclass

from specint.records import License

_NC_ND_MARKERS = ("by-nc", "bync", "by-nd", "bynd", "noncommercial", "no-derivatives")


@dataclass(frozen=True)
class LicenseVerdict:
    license: License
    confidence: float

    @property
    def is_redistributable(self) -> bool:
        return self.license.is_redistributable

    def strict_ok(self, min_confidence: float = 0.8) -> bool:
        return self.is_redistributable and self.confidence >= min_confidence


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace(" ", "")


def _license_from_url(url_norm: str) -> License | None:
    if not url_norm:
        return None
    if any(m in url_norm for m in _NC_ND_MARKERS):
        return License.RESTRICTED
    if "publicdomain/zero" in url_norm or "/cc0" in url_norm or "cc0-1.0" in url_norm:
        return License.CC0
    if "by-sa" in url_norm or "bysa" in url_norm:
        return License.CC_BY_SA
    if (
        "/by/" in url_norm
        or url_norm.endswith("/by")
        or "creativecommons.org/licenses/by/" in url_norm
        or url_norm.endswith("cc-by")
    ):
        return License.CC_BY
    if "publicdomain" in url_norm or "/pdm/" in url_norm or url_norm.endswith("pdm"):
        return License.PUBLIC_DOMAIN
    return None


def _license_from_short(short_norm: str) -> License | None:
    if not short_norm:
        return None
    if any(m in short_norm for m in _NC_ND_MARKERS):
        return License.RESTRICTED
    if short_norm.startswith("cc0") or short_norm == "zero":
        return License.CC0
    if "by-sa" in short_norm or "bysa" in short_norm:
        return License.CC_BY_SA
    if short_norm.startswith("cc-by") or short_norm.startswith("ccby") or short_norm == "by":
        return License.CC_BY
    if (
        short_norm == "pd"
        or "publicdomain" in short_norm
        or short_norm == "pdm"
        or "noknowncopyright" in short_norm
        or "no-known-copyright" in short_norm
    ):
        return License.PUBLIC_DOMAIN
    return None


def classify(url: str | None = None, short_name: str | None = None) -> LicenseVerdict:
    """Classify a license from a URL and/or a short-name string.

    Both inputs are optional. When both are present and agree, confidence
    is 0.95; when they disagree the URL wins (URLs are more machine-
    curated) and confidence drops to 0.80.
    """
    url_norm = _norm(url)
    short_norm = _norm(short_name)

    from_url = _license_from_url(url_norm)
    from_short = _license_from_short(short_norm)

    if from_url is not None and from_short is not None:
        if from_url == from_short:
            return LicenseVerdict(from_url, 0.95)
        if from_url is License.RESTRICTED or from_short is License.RESTRICTED:
            return LicenseVerdict(License.RESTRICTED, 0.95)
        return LicenseVerdict(from_url, 0.80)

    if from_url is not None:
        return LicenseVerdict(from_url, 0.80 if not short_norm else 0.85)

    if from_short is not None:
        return LicenseVerdict(from_short, 0.80)

    combined = f"{url_norm} {short_norm}".strip()
    if combined:
        if "public domain" in combined or "publicdomain" in combined:
            return LicenseVerdict(License.PUBLIC_DOMAIN, 0.50)
        if any(m in combined for m in _NC_ND_MARKERS):
            return LicenseVerdict(License.RESTRICTED, 0.90)

    return LicenseVerdict(License.UNKNOWN, 0.0)
