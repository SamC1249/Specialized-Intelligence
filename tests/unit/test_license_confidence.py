from __future__ import annotations

import pytest

from specint.license_confidence import (
    filter_by_confidence,
    score_license_confidence,
    tag_records,
)
from specint.records import License, Provenance, VideoRecord


def _rec(**kwargs) -> VideoRecord:
    base = {
        "id": "src:1",
        "source": "wikimedia",
        "source_native_id": "1",
        "url": "https://example.org/p",
        "title": "Pasta carbonara",
        "license": License.CC_BY,
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "provenance": Provenance(extractor="t"),
    }
    base.update(kwargs)
    return VideoRecord(**base)


def test_unknown_license_is_zero():
    r = _rec(license=License.UNKNOWN, license_url=None)
    assert score_license_confidence(r) == 0.0


def test_restricted_license_is_zero():
    r = _rec(license=License.RESTRICTED, license_url=None)
    assert score_license_confidence(r) == 0.0


def test_clean_record_high_confidence():
    r = _rec()
    score = score_license_confidence(r)
    assert score >= 0.9


def test_contradiction_caps_confidence():
    r = _rec(description="Free for non-commercial use only")
    score = score_license_confidence(r)
    assert score <= 0.2


def test_unknown_source_drops_bonus():
    r = _rec(source="other_open", license_url=None)
    # base 0.6 + 0.2 (no contradiction) = 0.8 (no known-clean +0.1)
    assert score_license_confidence(r) == pytest.approx(0.8)


def test_tag_records_pairs_each():
    r1 = _rec(id="a")
    r2 = _rec(id="b", license=License.UNKNOWN, license_url=None)
    tagged = tag_records([r1, r2])
    assert [t[0].id for t in tagged] == ["a", "b"]
    assert tagged[0][1] > tagged[1][1]


def test_filter_by_confidence_threshold():
    r1 = _rec(id="a")
    r2 = _rec(id="b", description="non-commercial only")
    kept = filter_by_confidence([r1, r2], threshold=0.5)
    assert [k.id for k in kept] == ["a"]
