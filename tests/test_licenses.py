from specint.quality.licenses import classify, classify_any
from specint.records import License


def test_classify_cc_by_variants():
    for value in [
        "CC BY 4.0",
        "cc-by 3.0",
        "CC_BY-4.0",
        "https://creativecommons.org/licenses/by/4.0/",
        "Attribution 3.0 Unported",
    ]:
        assert classify(value) is License.CC_BY, value


def test_classify_share_alike_variants():
    for value in [
        "CC BY-SA 4.0",
        "cc_by_sa",
        "https://creativecommons.org/licenses/by-sa/3.0/",
        "Attribution-ShareAlike 4.0",
    ]:
        assert classify(value) is License.CC_BY_SA, value


def test_classify_nc_and_nd_are_restricted_not_unknown():
    for value in [
        "CC BY-NC 4.0",
        "cc by-nc-sa",
        "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "CC BY-ND 3.0",
        "All Rights Reserved",
        "PROPRIETARY",
    ]:
        assert classify(value) is License.RESTRICTED, value


def test_classify_cc0_and_public_domain():
    assert classify("CC0 1.0") is License.CC0
    assert classify("https://creativecommons.org/publicdomain/zero/1.0/") is License.CC0
    assert classify("Public Domain") is License.PUBLIC_DOMAIN
    assert classify("No known copyright restrictions") is License.PUBLIC_DOMAIN
    assert classify("US Government Work") is License.PUBLIC_DOMAIN


def test_classify_empty_and_ambiguous():
    assert classify(None) is License.UNKNOWN
    assert classify("") is License.UNKNOWN
    assert classify("some random string") is License.UNKNOWN


def test_classify_any_prefers_first_hit():
    result = classify_any(None, "creative garbage", "CC BY 4.0")
    assert result is License.CC_BY


def test_classify_by_nc_not_treated_as_by():
    assert classify("https://creativecommons.org/licenses/by-nc/4.0/") is License.RESTRICTED
