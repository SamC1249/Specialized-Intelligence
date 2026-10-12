"""Training-corpus eligibility invariants.

Protects against risk #1 of the seed adversarial plan: a mis-classified
`License.UNKNOWN` record silently leaking into a training-eligible set.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specint.quality import filter_for_training, training_eligible
from specint.records import License, Provenance, VideoRecord


def _rec(license_: License, *, author: str | None = "Alice") -> VideoRecord:
    return VideoRecord(
        id=f"test:{license_.value}:{author or 'none'}",
        source="test",
        source_native_id=license_.value,
        url="https://example.test/video",
        title="A cooking video",
        description="",
        license=license_,
        author=author,
        published_at=datetime(2024, 1, 1, tzinfo=UTC),
        provenance=Provenance(extractor="tests.test_safety"),
    )


def test_unknown_is_never_eligible() -> None:
    assert not training_eligible(_rec(License.UNKNOWN))


def test_restricted_is_never_eligible() -> None:
    assert not training_eligible(_rec(License.RESTRICTED))


def test_cc_by_requires_author() -> None:
    assert training_eligible(_rec(License.CC_BY, author="Alice"))
    assert not training_eligible(_rec(License.CC_BY, author=None))
    assert not training_eligible(_rec(License.CC_BY, author=""))
    assert not training_eligible(_rec(License.CC_BY, author="   "))


def test_cc0_is_eligible_without_author() -> None:
    assert training_eligible(_rec(License.CC0, author=None))
    assert training_eligible(_rec(License.PUBLIC_DOMAIN, author=None))
    assert training_eligible(_rec(License.OTHER_FREE, author=None))


def test_filter_for_training_drops_unknown_and_restricted() -> None:
    records = [
        _rec(License.CC0, author=None),
        _rec(License.UNKNOWN),
        _rec(License.RESTRICTED),
        _rec(License.CC_BY, author="Attributed"),
        _rec(License.CC_BY, author=None),
    ]
    eligible = filter_for_training(records)

    assert len(eligible) == 2
    assert {r.license for r in eligible} == {License.CC0, License.CC_BY}
    for r in eligible:
        assert r.license is not License.UNKNOWN
        assert r.license is not License.RESTRICTED
