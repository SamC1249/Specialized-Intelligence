"""Unit tests for the license normalization layer.

These are the *contract* tests for the only piece of business logic that
absolutely cannot regress: what we will and will not put into a training
shard.
"""

from __future__ import annotations

import pytest

from specialized_intelligence.licenses import (
    LicenseNorm,
    is_training_eligible,
    normalize_license,
    policy_for,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("creativeCommon", LicenseNorm.CC_BY),
        ("CC0", LicenseNorm.CC0),
        ("cc0", LicenseNorm.CC0),
        ("CC-BY-4.0", LicenseNorm.CC_BY),
        ("cc-by-sa-4.0", LicenseNorm.CC_BY_SA),
        ("PublicDomain", LicenseNorm.PD),
        ("by-nc-sa", LicenseNorm.CC_BY_NC_SA),
        ("by-nd", LicenseNorm.CC_BY_ND),
        ("", LicenseNorm.UNKNOWN),
        ("   ", LicenseNorm.UNKNOWN),
        ("not-a-license", LicenseNorm.UNKNOWN),
        ("youtube", LicenseNorm.UNKNOWN),
    ],
)
def test_normalize_known_tags(raw: str, expected: LicenseNorm) -> None:
    assert normalize_license(raw) is expected


def test_normalize_none_returns_unknown() -> None:
    assert normalize_license(None) is LicenseNorm.UNKNOWN


@pytest.mark.parametrize(
    "lic",
    [LicenseNorm.CC0, LicenseNorm.PD, LicenseNorm.CC_BY, LicenseNorm.CC_BY_SA],
)
def test_training_eligible_licenses(lic: LicenseNorm) -> None:
    pol = policy_for(lic)
    assert pol.eligible_for_training is True
    assert pol.may_redistribute_bytes is True


@pytest.mark.parametrize(
    "lic",
    [
        LicenseNorm.CC_BY_ND,
        LicenseNorm.CC_BY_NC,
        LicenseNorm.CC_BY_NC_SA,
        LicenseNorm.CC_BY_NC_ND,
        LicenseNorm.UNKNOWN,
    ],
)
def test_non_training_licenses(lic: LicenseNorm) -> None:
    pol = policy_for(lic)
    assert pol.eligible_for_training is False
    assert pol.may_redistribute_bytes is False


def test_share_alike_propagation() -> None:
    """CC-BY-SA and CC-BY-NC-SA must require share-alike on derivatives."""
    assert policy_for(LicenseNorm.CC_BY_SA).requires_share_alike is True
    assert policy_for(LicenseNorm.CC_BY_NC_SA).requires_share_alike is True
    assert policy_for(LicenseNorm.CC_BY).requires_share_alike is False
    assert policy_for(LicenseNorm.CC0).requires_share_alike is False


def test_is_training_eligible_convenience() -> None:
    assert is_training_eligible("CC-BY-4.0") is True
    assert is_training_eligible("by-nc") is False
    assert is_training_eligible(None) is False


def test_every_license_has_a_policy() -> None:
    """Adding a new LicenseNorm without a policy must fail loudly."""
    for lic in LicenseNorm:
        pol = policy_for(lic)
        assert pol is not None
