"""Legal/TDM opt-out signals for collected records.

Three separate signals are captured per source host:

- **`robots.txt`** — RFC 9309 style, evaluated for our declared user-agent
  (`specint`) with the standard longest-match precedence. Silence means
  "allowed" per the RFC.
- **`/.well-known/tdmrep.json`** — TDM Reservation Protocol (W3C CG,
  aligned to EU AI Act Article 53 recital 105). Silence means "not
  reserved" i.e. TDM is allowed for scientific research; a matching
  `tdm-reservation: 1` reserves rights and we must exclude.
- **`ai.txt`** — Spawning-style AI opt-out (`User-Agent: <bot>` blocks
  with `Disallow:` patterns). Silence means "no signal", not "allowed".

All parsers here are **pure**: they take strings and return typed
results. The live fetcher is gated behind `SPECINT_RUN_INTEGRATION=1`
so CI stays offline.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_AGENT = "specint"


class TdmStatus(str, Enum):  # noqa: UP042 - Pydantic v2 handles classic str-Enum reliably
    RESERVED = "reserved"
    ALLOWED = "allowed"
    ABSENT = "absent"


class RightsSignal(BaseModel):
    """Immutable snapshot of the rights signals for one source host."""

    model_config = ConfigDict(frozen=True)

    source_url: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    robots_allowed: bool | None = None
    tdmrep: TdmStatus = TdmStatus.ABSENT
    ai_txt: dict[str, bool] | None = None
    notes: str = ""

    @property
    def is_permitted(self) -> bool:
        """True iff every present signal allows crawling.

        Silence-means-allowed for robots and TDMRep (per their specs);
        silence-means-refusal for ai.txt when a wildcard block is present.
        """
        if self.robots_allowed is False:
            return False
        if self.tdmrep is TdmStatus.RESERVED:
            return False
        if self.ai_txt is not None:
            explicit = self.ai_txt.get(DEFAULT_AGENT)
            if explicit is False:
                return False
            wildcard = self.ai_txt.get("*")
            if explicit is None and wildcard is False:
                return False
        return True


_ROBOTS_TOKEN_RE = re.compile(r"^\s*([A-Za-z-]+)\s*:\s*(.*?)\s*(?:#.*)?$")


def _iter_robots_groups(text: str) -> Iterable[tuple[list[str], list[tuple[str, str]]]]:
    """Yield (user_agents, [(directive, value)]) groups from a robots.txt."""
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    at_agents = True
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        m = _ROBOTS_TOKEN_RE.match(line)
        if not m:
            continue
        key = m.group(1).lower()
        value = m.group(2).strip()
        if key == "user-agent":
            if not at_agents and (agents or rules):
                yield agents, rules
                agents, rules = [], []
            agents.append(value.lower())
            at_agents = True
        else:
            at_agents = False
            rules.append((key, value))
    if agents or rules:
        yield agents, rules


def _robots_pattern_matches(pattern: str, path: str) -> bool:
    """RFC 9309 style pattern matching, supports `*` and end-anchor `$`."""
    if not pattern:
        return False
    anchor_end = pattern.endswith("$")
    if anchor_end:
        pattern = pattern[:-1]
    parts = pattern.split("*")
    idx = 0
    for i, part in enumerate(parts):
        if i == 0:
            if not path.startswith(part):
                return False
            idx = len(part)
            continue
        found = path.find(part, idx)
        if found < 0:
            return False
        idx = found + len(part)
    if anchor_end:
        return idx == len(path)
    return True


def parse_robots(text: str, agent: str = DEFAULT_AGENT, path: str = "/") -> bool:
    """Return True if `agent` is allowed to fetch `path` per this robots.txt.

    Uses longest-match precedence between Allow and Disallow, and picks
    the most specific matching user-agent group. Silence means allowed.
    """
    if not text:
        return True
    agent_lc = agent.lower()
    best_agent_specificity = -1
    matched_rules: list[tuple[str, str]] = []
    for agents, rules in _iter_robots_groups(text):
        specificity = -1
        for a in agents:
            if a == agent_lc:
                specificity = max(specificity, 2)
            elif a == "*":
                specificity = max(specificity, 1)
        if specificity > best_agent_specificity:
            best_agent_specificity = specificity
            matched_rules = rules
        elif specificity == best_agent_specificity and specificity >= 0:
            matched_rules = matched_rules + rules
    if best_agent_specificity < 0:
        return True

    best_allow = -1
    best_disallow = -1
    for directive, value in matched_rules:
        if directive == "allow" and _robots_pattern_matches(value, path):
            best_allow = max(best_allow, len(value))
        elif directive == "disallow":
            if value == "":
                continue
            if _robots_pattern_matches(value, path):
                best_disallow = max(best_disallow, len(value))
    if best_disallow < 0:
        return True
    return best_allow >= best_disallow


def _iter_tdmrep_entries(data: Any) -> Iterable[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
    elif isinstance(data, dict):
        entries = data.get("tdmrep")
        if isinstance(entries, list):
            for item in entries:
                if isinstance(item, dict):
                    yield item
        else:
            yield data


def parse_tdmrep_json(text: str, location: str = "/") -> TdmStatus:
    """Parse a `/.well-known/tdmrep.json` payload.

    Returns:
      RESERVED  — a matching entry declares `tdm-reservation: 1`.
      ALLOWED   — a matching entry declares `tdm-reservation: 0`.
      ABSENT    — no entry applies (silence == allowed by spec, but we
                  keep it distinct so callers can log the difference).
    """
    if not text:
        return TdmStatus.ABSENT
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return TdmStatus.ABSENT
    best_match = -1
    best_status = TdmStatus.ABSENT
    for entry in _iter_tdmrep_entries(data):
        loc = entry.get("location") or entry.get("l") or "/"
        if not isinstance(loc, str):
            continue
        if not location.startswith(loc):
            continue
        res = entry.get("tdm-reservation")
        if res is None:
            res = entry.get("r")
        specificity = len(loc)
        if specificity <= best_match:
            continue
        best_match = specificity
        if res in (1, "1", True):
            best_status = TdmStatus.RESERVED
        elif res in (0, "0", False):
            best_status = TdmStatus.ALLOWED
        else:
            best_status = TdmStatus.ABSENT
    return best_status


_TDM_HEADER_RE = re.compile(r"tdm-reservation\s*=\s*(\d)", re.IGNORECASE)


def parse_tdmrep_header(headers: dict[str, str]) -> TdmStatus:
    """Parse the `TDM-Reservation` HTTP response header (RFC-9457 style)."""
    for name, value in headers.items():
        if name.lower() != "tdm-reservation":
            continue
        if value.strip() == "1":
            return TdmStatus.RESERVED
        if value.strip() == "0":
            return TdmStatus.ALLOWED
        m = _TDM_HEADER_RE.search(value)
        if m:
            return TdmStatus.RESERVED if m.group(1) == "1" else TdmStatus.ALLOWED
    return TdmStatus.ABSENT


def parse_ai_txt(text: str) -> dict[str, bool]:
    """Parse a Spawning-style `ai.txt` file.

    Returns a dict of `{agent_name_lower: is_allowed}`. `is_allowed` is
    True when a `User-Agent` group declares no `Disallow: /`; False when
    a wildcard disallow is present. Wildcard agent is stored as `"*"`.
    """
    if not text:
        return {}
    result: dict[str, bool] = {}
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        m = _ROBOTS_TOKEN_RE.match(line)
        if not m:
            continue
        key = m.group(1).lower()
        value = m.group(2).strip().lower()
        if key == "user-agent":
            current = [value]
            for name in current:
                result.setdefault(name, True)
        elif key == "disallow" and current:
            if value in ("", "/", "*"):
                for name in current:
                    if value == "":
                        result.setdefault(name, True)
                    else:
                        result[name] = False
        elif key == "allow" and current:
            if value in ("", "/", "*"):
                for name in current:
                    result[name] = True
    return result


def fetch_rights(base_url: str, agent: str = DEFAULT_AGENT) -> RightsSignal:
    """Live-fetch the three signals for a host.

    Gated by `SPECINT_RUN_INTEGRATION=1` so unit tests never touch the
    network. Import inside the function so `httpx` is not required for
    the pure-parser code paths.
    """
    if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        return RightsSignal(source_url=base_url, notes="skipped: offline")
    import httpx

    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    client = httpx.Client(timeout=10.0, headers={"User-Agent": f"{agent}/0.1"})
    try:
        robots_allowed: bool | None = None
        try:
            resp = client.get(f"{root}/robots.txt")
            if resp.status_code == 200:
                robots_allowed = parse_robots(resp.text, agent=agent, path=parsed.path or "/")
            elif resp.status_code in (401, 403):
                robots_allowed = False
            else:
                robots_allowed = True
        except Exception:
            robots_allowed = None

        tdm_status = TdmStatus.ABSENT
        try:
            resp = client.get(f"{root}/.well-known/tdmrep.json")
            if resp.status_code == 200:
                tdm_status = parse_tdmrep_json(resp.text, location=parsed.path or "/")
        except Exception:
            pass

        ai_map: dict[str, bool] | None = None
        try:
            resp = client.get(f"{root}/ai.txt")
            if resp.status_code == 200:
                ai_map = parse_ai_txt(resp.text)
        except Exception:
            pass
        return RightsSignal(
            source_url=base_url,
            robots_allowed=robots_allowed,
            tdmrep=tdm_status,
            ai_txt=ai_map,
        )
    finally:
        client.close()


def is_source_permitted(signal: RightsSignal | None) -> bool:
    """None (never checked) is treated as *not permitted* — fail closed."""
    if signal is None:
        return False
    return signal.is_permitted
