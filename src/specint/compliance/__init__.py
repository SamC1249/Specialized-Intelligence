"""Compliance signals (robots.txt, TDMRep, ai.txt) for TDM opt-out capture."""

from specint.compliance.rights import (
    RightsSignal,
    TdmStatus,
    fetch_rights,
    is_source_permitted,
    parse_ai_txt,
    parse_robots,
    parse_tdmrep_header,
    parse_tdmrep_json,
)

__all__ = [
    "RightsSignal",
    "TdmStatus",
    "fetch_rights",
    "is_source_permitted",
    "parse_ai_txt",
    "parse_robots",
    "parse_tdmrep_header",
    "parse_tdmrep_json",
]
