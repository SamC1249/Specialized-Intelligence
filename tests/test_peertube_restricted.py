"""PeerTube: restricted licenses must be filtered out entirely."""

from __future__ import annotations

import json
from pathlib import Path

from specint.records import SourceQuery
from specint.sources.peertube import PeerTubeSource


def test_restricted_only_yields_no_records(fixtures_dir: Path):
    raw = json.loads((fixtures_dir / "peertube/restricted_only.json").read_text())
    records = PeerTubeSource().parse(raw, SourceQuery(terms=["cooking"]))
    assert records == []
