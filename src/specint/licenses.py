"""Unified license classifier.

Historically each adapter carried its own ``_coerce_license`` /
``_license_from_url`` helper (see W5 in ``docs/plan-2026-08-25.md``).
Duplication meant no single test proved we classified adversarial
license strings correctly, so a mis-parse could ship license-dirty
records without any adapter test noticing.

This module exposes one canonical entry point:

    classify(text: str | None, url: str | None = None) -> License

The function is pure, deterministic, order-independent for its two
inputs, and MUST default to :pydata:`License.UNKNOWN` when the inputs
are missing, ambiguous, or match a known non-redistributable variant
(NC / ND). Callers may then either drop the record or store it as a
URL-only pointer, per AGENTS.md rule #1.

Design notes:

- We match on both the human-readable short name (e.g. ``"CC BY-SA 4.0"``)
  and the licence URL (e.g. ``https://creativecommons.org/licenses/by-sa/4.0``)
  because different sources supply different subsets.
- Non-commercial (``BY-NC``) and no-derivatives (``BY-ND``) variants map
  to :pydata:`License.RESTRICTED`. They ARE Creative Commons but they are
  NOT redistributable for our training use case.
- Public Domain Mark and PDM-1.0 map to :pydata:`License.PUBLIC_DOMAIN`.
- ``CC0`` and ``publicdomain/zero`` map to :pydata:`License.CC0`.
- The ``OTHER_FREE`` tier is reserved for verifiably-redistributable
  non-CC licences (WTFPL, Unlicense, permissive gov works). We do
  *not* auto-classify into ``OTHER_FREE`` from free text yet because
  false positives would leak restricted media into a training set.
"""

from __future__ import annotations

from specint.records import License

_NC_MARKERS = ("by-nc", "byncnc", "noncommercial", "non-commercial")
_ND_MARKERS = ("by-nd", "bynd", "noderivatives", "no-derivatives", "no derivs")
_SA_MARKERS = ("by-sa", "bysa", "sharealike", "share-alike", "share alike")
_BY_MARKERS = (
    "by/",
    "cc-by",
    "ccby",
    "cc by",
    "creative commons attribution",
    "attribution",
)
_CC0_MARKERS = ("cc0", "publicdomain/zero", "public domain dedication", "no rights reserved")
_PD_MARKERS = (
    "public domain mark",
    "publicdomainmark",
    "pdm-1.0",
    "pdm 1.0",
    "publicdomain",
    "public-domain",
    "public domain",
    "united states government work",
    "u.s. government work",
    "us gov work",
)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace("_", "-")


def classify(text: str | None, url: str | None = None) -> License:
    """Return the canonical :class:`License` for a licence blob.

    ``text`` is a human-readable short name or long description.
    ``url`` is a canonical licence URL (often creativecommons.org).
    Either may be ``None``; both being empty returns
    :pydata:`License.UNKNOWN`.
    """
    t = _normalize(text)
    u = _normalize(url)
    haystack = f"{t} {u}".strip()
    if not haystack:
        return License.UNKNOWN

    if any(m in haystack for m in _NC_MARKERS):
        return License.RESTRICTED
    if any(m in haystack for m in _ND_MARKERS):
        return License.RESTRICTED

    if any(m in haystack for m in _CC0_MARKERS):
        return License.CC0

    if any(m in haystack for m in _SA_MARKERS):
        return License.CC_BY_SA

    if any(m in haystack for m in _PD_MARKERS):
        return License.PUBLIC_DOMAIN

    if any(m in haystack for m in _BY_MARKERS):
        return License.CC_BY

    return License.UNKNOWN


__all__ = ["License", "classify"]
