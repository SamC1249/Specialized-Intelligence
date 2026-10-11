"""Schema-contract test.

`db_structured.md` is the stated single source of truth for the
canonical data models. Nothing in CI previously enforced that the
Pydantic classes still matched the markdown table. If the two drift,
backend/frontend contracts rot silently.

This test parses the `VideoRecord`, `Provenance`, `SourceQuery`, and
`BenchmarkResult` tables out of the markdown and asserts the field
names declared there are exactly the fields on the Pydantic model.

It also enforces that every value of the documented `License` enum is
present on the Python enum.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specint.records import BenchmarkResult, License, Provenance, SourceQuery, VideoRecord

DB_DOC = Path(__file__).resolve().parent.parent / "db_structured.md"

_SECTION_RE = re.compile(r"^##\s+`(?P<name>[A-Za-z_]+)`")
_FIELD_ROW_RE = re.compile(r"^\|\s*`(?P<field>[a-zA-Z_][a-zA-Z0-9_]*)`\s*\|")
_ENUM_ROW_RE = re.compile(r"^\|\s*`(?P<value>[A-Z0-9_]+)`\s*\|")


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Return {section_name: [field_or_value, ...]} for every `##` block."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = _SECTION_RE.match(line)
        if m:
            current = m.group("name")
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        if line.startswith("| Field") or line.startswith("| Value") or line.startswith("|---"):
            continue
        field = _FIELD_ROW_RE.match(line)
        if field:
            sections[current].append(field.group("field"))
            continue
        enum = _ENUM_ROW_RE.match(line)
        if enum:
            sections[current].append(enum.group("value"))
    return sections


@pytest.fixture(scope="module")
def db_sections() -> dict[str, list[str]]:
    assert DB_DOC.exists(), f"db_structured.md missing at {DB_DOC}"
    return _parse_sections(DB_DOC.read_text())


@pytest.mark.parametrize(
    "section,model",
    [
        ("VideoRecord", VideoRecord),
        ("Provenance", Provenance),
        ("SourceQuery", SourceQuery),
        ("BenchmarkResult", BenchmarkResult),
    ],
)
def test_db_markdown_matches_pydantic_model(db_sections, section, model):
    documented = set(db_sections.get(section, []))
    code = set(model.model_fields.keys())
    assert documented, f"no fields parsed from `## {section}` block in db_structured.md"

    missing_in_code = documented - code
    missing_in_doc = code - documented
    assert not missing_in_code, (
        f"db_structured.md declares `{section}` fields that are missing from the Pydantic "
        f"model: {sorted(missing_in_code)}"
    )
    assert not missing_in_doc, (
        f"Pydantic model `{section}` has fields not documented in db_structured.md: "
        f"{sorted(missing_in_doc)}"
    )


def test_license_enum_matches_doc(db_sections):
    documented = set(db_sections.get("License", []))
    code = {member.name for member in License}
    assert documented, "no License values parsed from db_structured.md"
    assert documented == code, (
        "License enum drift between db_structured.md and specint.records.License: "
        f"doc-only={sorted(documented - code)}, code-only={sorted(code - documented)}"
    )
