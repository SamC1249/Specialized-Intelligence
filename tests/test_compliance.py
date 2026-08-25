"""Compliance signal parsers — pure, offline tests."""

from __future__ import annotations

from pathlib import Path

from specint.compliance import (
    RightsSignal,
    TdmStatus,
    is_source_permitted,
    parse_ai_txt,
    parse_robots,
    parse_tdmrep_header,
    parse_tdmrep_json,
)

FIX = Path(__file__).parent / "fixtures" / "rights"


def _text(name: str) -> str:
    return (FIX / name).read_text()


def test_robots_specint_specific_group_wins_over_wildcard():
    text = _text("robots_youtube.txt")
    assert parse_robots(text, agent="specint", path="/watch") is True
    assert parse_robots(text, agent="specint", path="/embed") is False
    assert parse_robots(text, agent="somebot", path="/watch") is False


def test_robots_longest_match_allow_disallow():
    text = _text("robots_wikimedia.txt")
    assert parse_robots(text, agent="specint", path="/w/api.php") is True
    assert parse_robots(text, agent="genericbot", path="/w/api.php") is False
    assert parse_robots(text, agent="genericbot", path="/wiki/Special:Search") is True


def test_robots_silence_means_allowed():
    assert parse_robots("", agent="specint", path="/anything") is True
    assert parse_robots(_text("robots_common_crawl.txt"), path="/anything") is True


def test_robots_archive_org_specific_disallow():
    text = _text("robots_archive_org.txt")
    assert parse_robots(text, path="/details/xyz") is True
    assert parse_robots(text, path="/account/") is False


def test_tdmrep_json_reserved_wins_by_path_specificity():
    text = _text("tdmrep_reserved.json")
    assert parse_tdmrep_json(text, location="/premium/foo") is TdmStatus.RESERVED
    assert parse_tdmrep_json(text, location="/public/bar") is TdmStatus.ALLOWED
    assert parse_tdmrep_json(text, location="/other") is TdmStatus.ABSENT


def test_tdmrep_json_allowed_list():
    text = _text("tdmrep_allowed.json")
    assert parse_tdmrep_json(text, location="/") is TdmStatus.ALLOWED
    assert parse_tdmrep_json(text, location="/whatever") is TdmStatus.ALLOWED


def test_tdmrep_header_reserved_and_allowed():
    assert parse_tdmrep_header({"TDM-Reservation": "1"}) is TdmStatus.RESERVED
    assert parse_tdmrep_header({"tdm-reservation": "0"}) is TdmStatus.ALLOWED
    assert parse_tdmrep_header({"other": "x"}) is TdmStatus.ABSENT


def test_ai_txt_carve_out_allows_specint_only():
    ai = parse_ai_txt(_text("ai.txt"))
    assert ai["*"] is False
    assert ai["specint"] is True
    assert ai["gptbot"] is False


def test_rights_signal_permission_matrix():
    fully_allowed = RightsSignal(
        source_url="https://x.test",
        robots_allowed=True,
        tdmrep=TdmStatus.ALLOWED,
        ai_txt={"specint": True, "*": False},
    )
    assert fully_allowed.is_permitted
    assert is_source_permitted(fully_allowed)

    robots_denied = fully_allowed.model_copy(update={"robots_allowed": False})
    assert not robots_denied.is_permitted

    tdm_reserved = fully_allowed.model_copy(update={"tdmrep": TdmStatus.RESERVED})
    assert not tdm_reserved.is_permitted

    wildcard_block_no_carveout = RightsSignal(
        source_url="https://y.test",
        robots_allowed=True,
        tdmrep=TdmStatus.ABSENT,
        ai_txt={"*": False},
    )
    assert not wildcard_block_no_carveout.is_permitted

    silent = RightsSignal(source_url="https://z.test")
    assert silent.is_permitted

    assert not is_source_permitted(None)
