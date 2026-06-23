from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def load_json(fixtures_dir: Path):
    def _load(rel: str):
        return json.loads((fixtures_dir / rel).read_text())

    return _load


@pytest.fixture
def load_text(fixtures_dir: Path):
    def _load(rel: str) -> str:
        return (fixtures_dir / rel).read_text()

    return _load
