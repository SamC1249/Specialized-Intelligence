"""Schema drift guard.

Attack D2 from `docs/artifacts/2026-09-18-adversarial-findings.md`:
``db_structured.md`` is the single source of truth per repo rules, but
nothing enforces that its documented fields match the Pydantic models in
``src/specint/records.py``. If they drift, downstream API/UI contracts
silently break.

This test parses the Markdown tables in ``db_structured.md`` and asserts
bidirectional coverage:

  * every field documented in the markdown exists in the model;
  * every model field is documented in the markdown.

If you add a field, update both places.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specint.records import (
    BenchmarkResult,
    Provenance,
    SourceQuery,
    VideoRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_STRUCTURED_MD = REPO_ROOT / "db_structured.md"

SECTION_TO_MODEL = {
    "VideoRecord": VideoRecord,
    "Provenance": Provenance,
    "SourceQuery": SourceQuery,
    "BenchmarkResult": BenchmarkResult,
}

DOCUMENTED_EXTRAS = {
    "VideoRecord": {"quality_score"},
}


_H2 = re.compile(r"^##\s+`?(?P<name>[A-Za-z_]+)`?", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\|\s*`(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)`\s*\|")


def _extract_sections(md: str) -> dict[str, str]:
    matches = list(_H2.finditer(md))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group("name")
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        sections[name] = md[start:end]
    return sections


def _fields_in_section(section_body: str) -> set[str]:
    fields: set[str] = set()
    for line in section_body.splitlines():
        m = _TABLE_ROW.match(line.strip())
        if m and m.group("field").lower() not in {"field"}:
            fields.add(m.group("field"))
    return fields


@pytest.fixture
def sections() -> dict[str, str]:
    assert DB_STRUCTURED_MD.exists(), "db_structured.md is missing"
    return _extract_sections(DB_STRUCTURED_MD.read_text())


@pytest.mark.parametrize("section_name,model", list(SECTION_TO_MODEL.items()))
def test_documented_fields_exist_on_model(section_name, model, sections):
    body = sections.get(section_name)
    assert body is not None, f"section '## `{section_name}`' missing from db_structured.md"

    documented = _fields_in_section(body)
    model_fields = set(model.model_fields.keys())

    missing_on_model = documented - model_fields
    assert not missing_on_model, (
        f"{section_name}: fields documented in db_structured.md but not on the "
        f"Pydantic model: {sorted(missing_on_model)}"
    )


@pytest.mark.parametrize("section_name,model", list(SECTION_TO_MODEL.items()))
def test_model_fields_are_documented(section_name, model, sections):
    body = sections.get(section_name)
    assert body is not None
    documented = _fields_in_section(body) | DOCUMENTED_EXTRAS.get(section_name, set())
    model_fields = set(model.model_fields.keys())

    missing_in_docs = model_fields - documented
    assert not missing_in_docs, (
        f"{section_name}: fields present on the Pydantic model but not in "
        f"db_structured.md: {sorted(missing_in_docs)}. "
        f"Update db_structured.md or add to DOCUMENTED_EXTRAS."
    )
