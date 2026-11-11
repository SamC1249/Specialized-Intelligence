"""Schema contract: `db_structured.md` is the single source of truth.

Parse the markdown field tables for every documented Pydantic model and
assert the field names match the live model exactly (bidirectional). Any
drift — a field added to the model without updating the doc, or vice
versa — fails CI. This is the most under-tested invariant in the repo.

Type-string normalization is intentionally loose (`str | None` ≡
`str|None` ≡ `Optional[str]`, etc.). We care about *what fields exist*
first; strict type equality is a later tightening tracked in
`docs/plan-2026-11-11.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specint.records import BenchmarkResult, Provenance, SourceQuery, VideoRecord

DOC = Path(__file__).resolve().parents[1] / "db_structured.md"

MODELS = {
    "VideoRecord": VideoRecord,
    "Provenance": Provenance,
    "SourceQuery": SourceQuery,
    "BenchmarkResult": BenchmarkResult,
}

_HEADER_RE = re.compile(r"^##\s+`([A-Za-z_][A-Za-z0-9_]*)`\s*\(Pydantic model\)")
_ROW_RE = re.compile(r"^\|\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*\|")


def _parse_doc_sections(markdown: str) -> dict[str, set[str]]:
    sections: dict[str, set[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        header = _HEADER_RE.match(line)
        if header:
            current = header.group(1)
            sections[current] = set()
            continue
        if current is None:
            continue
        if line.startswith("## "):
            current = None
            continue
        row = _ROW_RE.match(line)
        if not row:
            continue
        field = row.group(1)
        if field in {"Field", "Value"}:
            continue
        sections[current].add(field)
    return sections


@pytest.fixture(scope="module")
def doc_sections() -> dict[str, set[str]]:
    return _parse_doc_sections(DOC.read_text())


@pytest.mark.parametrize("model_name", sorted(MODELS))
def test_model_fields_match_doc(model_name: str, doc_sections: dict[str, set[str]]) -> None:
    assert model_name in doc_sections, (
        f"{model_name} has no ## `{model_name}` (Pydantic model) section in db_structured.md"
    )
    documented = doc_sections[model_name]
    declared = set(MODELS[model_name].model_fields)

    missing_in_model = documented - declared
    missing_in_doc = declared - documented
    assert not missing_in_model, (
        f"{model_name}: db_structured.md declares fields that the model does not have: "
        f"{sorted(missing_in_model)}"
    )
    assert not missing_in_doc, (
        f"{model_name}: model has fields not documented in db_structured.md: "
        f"{sorted(missing_in_doc)}. Update db_structured.md and rerun."
    )


def test_every_pydantic_model_section_has_a_known_model(doc_sections: dict[str, set[str]]) -> None:
    unknown = set(doc_sections) - set(MODELS)
    assert not unknown, (
        f"db_structured.md declares Pydantic model sections with no corresponding model in "
        f"specint.records: {sorted(unknown)}"
    )
