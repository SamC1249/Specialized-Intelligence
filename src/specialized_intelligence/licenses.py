"""License normalization and policy.

The single source of truth for what licenses we accept and what we may do
with each one. Cross-references `db_structured.md` section 1 and
`docs/artifacts/2026-06-23-legal-considerations.md` section 2.

Inputs:
    raw_tag: ``str`` — the license string returned by an upstream source
        (e.g. ``"creativeCommon"`` from the YouTube Data API,
        ``"CC-BY-SA-4.0"`` from Wikimedia, ``"by-nc-sa"`` from Vimeo).

Outputs:
    `LicenseNorm` enum member. Never returns ``None``; unknown inputs map
    to `LicenseNorm.UNKNOWN`. Unknown licenses are *never* eligible for
    training; they may be retained in the discovery table for audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LicenseNorm(StrEnum):
    """Closed enum of license classes we recognise.

    Members are strings so they serialize cleanly to Parquet/JSON.
    """

    CC0 = "CC0"
    PD = "PD"
    CC_BY = "CC_BY"
    CC_BY_SA = "CC_BY_SA"
    CC_BY_ND = "CC_BY_ND"
    CC_BY_NC = "CC_BY_NC"
    CC_BY_NC_SA = "CC_BY_NC_SA"
    CC_BY_NC_ND = "CC_BY_NC_ND"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LicensePolicy:
    """What we may do under a given normalized license.

    Attributes:
        eligible_for_training: clip bytes may enter a training shard.
        may_redistribute_bytes: we may persist & republish the raw bytes.
        requires_attribution: caller must propagate attribution downstream.
        requires_share_alike: derived dataset must be released SA.
    """

    eligible_for_training: bool
    may_redistribute_bytes: bool
    requires_attribution: bool
    requires_share_alike: bool


_POLICY: dict[LicenseNorm, LicensePolicy] = {
    LicenseNorm.CC0: LicensePolicy(True, True, False, False),
    LicenseNorm.PD: LicensePolicy(True, True, False, False),
    LicenseNorm.CC_BY: LicensePolicy(True, True, True, False),
    LicenseNorm.CC_BY_SA: LicensePolicy(True, True, True, True),
    # CC-BY-ND forbids derivative works; our pipeline always re-encodes & clips.
    LicenseNorm.CC_BY_ND: LicensePolicy(False, False, True, False),
    # CC-NC variants are research-only; never enter training shards.
    LicenseNorm.CC_BY_NC: LicensePolicy(False, False, True, False),
    LicenseNorm.CC_BY_NC_SA: LicensePolicy(False, False, True, True),
    LicenseNorm.CC_BY_NC_ND: LicensePolicy(False, False, True, False),
    LicenseNorm.UNKNOWN: LicensePolicy(False, False, True, False),
}


_ALIASES: dict[str, LicenseNorm] = {
    # YouTube Data API
    "creativecommon": LicenseNorm.CC_BY,
    "youtube": LicenseNorm.UNKNOWN,  # the default YT license, not reusable
    # Wikimedia / Commons style
    "cc0": LicenseNorm.CC0,
    "cc-zero": LicenseNorm.CC0,
    "publicdomain": LicenseNorm.PD,
    "public-domain": LicenseNorm.PD,
    "pd": LicenseNorm.PD,
    "cc-by": LicenseNorm.CC_BY,
    "cc-by-4.0": LicenseNorm.CC_BY,
    "cc-by-3.0": LicenseNorm.CC_BY,
    "cc-by-2.0": LicenseNorm.CC_BY,
    "cc-by-sa": LicenseNorm.CC_BY_SA,
    "cc-by-sa-4.0": LicenseNorm.CC_BY_SA,
    "cc-by-sa-3.0": LicenseNorm.CC_BY_SA,
    "cc-by-nd": LicenseNorm.CC_BY_ND,
    "cc-by-nd-4.0": LicenseNorm.CC_BY_ND,
    "cc-by-nc": LicenseNorm.CC_BY_NC,
    "cc-by-nc-4.0": LicenseNorm.CC_BY_NC,
    "cc-by-nc-sa": LicenseNorm.CC_BY_NC_SA,
    "cc-by-nc-sa-4.0": LicenseNorm.CC_BY_NC_SA,
    "cc-by-nc-nd": LicenseNorm.CC_BY_NC_ND,
    # Vimeo short codes
    "by": LicenseNorm.CC_BY,
    "by-sa": LicenseNorm.CC_BY_SA,
    "by-nd": LicenseNorm.CC_BY_ND,
    "by-nc": LicenseNorm.CC_BY_NC,
    "by-nc-sa": LicenseNorm.CC_BY_NC_SA,
    "by-nc-nd": LicenseNorm.CC_BY_NC_ND,
}


def normalize_license(raw_tag: str | None) -> LicenseNorm:
    """Map an upstream license tag onto the closed `LicenseNorm` enum.

    Args:
        raw_tag: license string as emitted by the source (may be ``None``).

    Returns:
        the corresponding `LicenseNorm`; ``UNKNOWN`` if we do not
        recognise the tag. Comparison is case-insensitive and ignores
        surrounding whitespace.
    """
    if raw_tag is None:
        return LicenseNorm.UNKNOWN
    key = raw_tag.strip().lower()
    if not key:
        return LicenseNorm.UNKNOWN
    return _ALIASES.get(key, LicenseNorm.UNKNOWN)


def policy_for(norm: LicenseNorm) -> LicensePolicy:
    """Return the `LicensePolicy` for a normalized license."""
    return _POLICY[norm]


def is_training_eligible(raw_tag: str | None) -> bool:
    """Convenience: True iff bytes under this license may enter training."""
    return policy_for(normalize_license(raw_tag)).eligible_for_training
