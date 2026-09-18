"""Unified license classification.

Every source used to roll its own string/URL matcher. That surface produced
subtly different answers for the same upstream license (e.g. Wikimedia's
``LicenseShortName`` value ``"CC BY 4.0"`` classified fine, but the
Archive.org URL ``https://creativecommons.org/licenses/by/4.0/`` had to hit
a bespoke branch). Centralising here means:

  * one regex table maintained per license family,
  * URL and human-readable strings evaluated by the same rules,
  * ``NC`` / ``ND`` variants are conservatively bucketed into
    :attr:`License.RESTRICTED` so we never accidentally mark them
    ``UNKNOWN`` (which would still exclude them from training but is
    weaker signal for provenance auditing).

The classifier is a pure function. Ambiguous inputs collapse to
:attr:`License.UNKNOWN`. Adapters may override with source-specific
knowledge but should prefer this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from specint.records import License

_WS_RE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    return _WS_RE.sub(" ", value.strip().lower())


@dataclass(frozen=True)
class _Rule:
    license: License
    patterns: tuple[re.Pattern[str], ...]


def _p(*regexes: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(r, re.IGNORECASE) for r in regexes)


# Order matters: NC/ND variants must match before the plain CC-BY family
# so we do not mislabel a NonCommercial licence as redistributable.
_RULES: tuple[_Rule, ...] = (
    _Rule(
        License.RESTRICTED,
        _p(
            r"\bby[\s\-_]?nc[\s\-_]?nd\b",
            r"\bby[\s\-_]?nc[\s\-_]?sa\b",
            r"\bby[\s\-_]?nc\b",
            r"\bby[\s\-_]?nd\b",
            r"licenses/by-nc",
            r"licenses/by-nd",
            r"licenses/nc",
            r"all\s+rights\s+reserved",
            r"copyrighted",
            r"proprietary",
        ),
    ),
    _Rule(
        License.CC0,
        _p(
            r"\bcc0\b",
            r"publicdomain/zero",
            r"creativecommons\.org/publicdomain/zero",
        ),
    ),
    _Rule(
        License.PUBLIC_DOMAIN,
        _p(
            r"public\s*domain",
            r"\bpdm\b",
            r"publicdomain/mark",
            r"no[\s\-]?known[\s\-]?(copyright|restrictions)",
            r"us\s*gov(ernment)?\s*work",
        ),
    ),
    _Rule(
        License.CC_BY_SA,
        _p(
            r"\bcc[\s\-_]?by[\s\-_]?sa\b",
            r"licenses/by-sa",
            r"attribution[\s\-]*share[\s\-]*alike",
        ),
    ),
    _Rule(
        License.CC_BY,
        _p(
            r"\bcc[\s\-_]?by\b(?![\s\-_]?(sa|nc|nd))",
            r"licenses/by/",
            r"licenses/by$",
            r"\battribution\b(?!.*(non|share|no\s*deriv))",
        ),
    ),
    _Rule(
        License.OTHER_FREE,
        _p(
            r"\bwtfpl\b",
            r"\bunlicense\b",
            r"free\s*art\s*license",
        ),
    ),
)


def classify(value: str | None) -> License:
    """Classify a license string or URL. Returns UNKNOWN on empty/ambiguous."""

    if value is None:
        return License.UNKNOWN
    text = _normalize(str(value))
    if not text:
        return License.UNKNOWN
    for rule in _RULES:
        for pattern in rule.patterns:
            if pattern.search(text):
                return rule.license
    return License.UNKNOWN


def classify_any(*candidates: str | None) -> License:
    """Try each candidate in order; return the first non-UNKNOWN result."""

    for candidate in candidates:
        result = classify(candidate)
        if result is not License.UNKNOWN:
            return result
    return License.UNKNOWN
