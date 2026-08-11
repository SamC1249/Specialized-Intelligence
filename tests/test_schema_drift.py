"""Guard against `db_structured.md` drifting from Pydantic models.

The doc is our single source of truth per the workspace user rule.
If a field is added to `VideoRecord` but not documented, or a doc row
is added without a matching model field, this test fails.

Fields intentionally *not* in the doc (e.g. `quality_score` which is a
derived, in-memory-only attachment) are listed in `INTERNAL_ONLY`.
"""

from __future__ import annotations

import re
from pathlib import Path

from specint.records import BenchmarkResult, License, Provenance, SourceQuery, VideoRecord

DOC = Path(__file__).parent.parent / "db_structured.md"

INTERNAL_ONLY: dict[str, set[str]] = {
    "VideoRecord": {"quality_score"},
    "BenchmarkResult": set(),
    "SourceQuery": set(),
    "Provenance": set(),
}


def _section_fields(doc_text: str, header: str) -> set[str]:
    """Extract the first column of the first Markdown table under a header."""
    pattern = re.compile(
        rf"##\s+`{re.escape(header)}`.*?\n(?P<body>(?:.*\n)+?)(?=\n##\s|\Z)",
        re.MULTILINE,
    )
    m = pattern.search(doc_text)
    assert m, f"section for `{header}` not found in db_structured.md"
    body = m.group("body")
    fields: set[str] = set()
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        first = cells[0]
        if first.lower() in {"field", "value", ":---", "---"} or set(first) <= {"-", ":"}:
            continue
        m2 = re.match(r"`([^`]+)`", first)
        if m2:
            fields.add(m2.group(1))
    return fields


def _model_fields(model: type) -> set[str]:
    return set(model.model_fields.keys())


def test_video_record_matches_doc():
    doc_text = DOC.read_text()
    doc_fields = _section_fields(doc_text, "VideoRecord")
    model_fields = _model_fields(VideoRecord) - INTERNAL_ONLY["VideoRecord"]
    assert doc_fields == model_fields, (
        f"VideoRecord drift.\n  only-in-doc: {doc_fields - model_fields}\n"
        f"  only-in-model: {model_fields - doc_fields}"
    )


def test_provenance_matches_doc():
    doc_text = DOC.read_text()
    doc_fields = _section_fields(doc_text, "Provenance")
    model_fields = _model_fields(Provenance) - INTERNAL_ONLY["Provenance"]
    assert doc_fields == model_fields, (
        f"Provenance drift.\n  only-in-doc: {doc_fields - model_fields}\n"
        f"  only-in-model: {model_fields - doc_fields}"
    )


def test_source_query_matches_doc():
    doc_text = DOC.read_text()
    doc_fields = _section_fields(doc_text, "SourceQuery")
    model_fields = _model_fields(SourceQuery) - INTERNAL_ONLY["SourceQuery"]
    assert doc_fields == model_fields, (
        f"SourceQuery drift.\n  only-in-doc: {doc_fields - model_fields}\n"
        f"  only-in-model: {model_fields - doc_fields}"
    )


def test_benchmark_result_matches_doc():
    doc_text = DOC.read_text()
    doc_fields = _section_fields(doc_text, "BenchmarkResult")
    model_fields = _model_fields(BenchmarkResult) - INTERNAL_ONLY["BenchmarkResult"]
    assert doc_fields == model_fields, (
        f"BenchmarkResult drift.\n  only-in-doc: {doc_fields - model_fields}\n"
        f"  only-in-model: {model_fields - doc_fields}"
    )


def test_license_enum_values_documented():
    doc_text = DOC.read_text()
    m = re.search(r"##\s+`License`.*?\n(?P<body>(?:.*\n)+?)(?=\n##\s|\Z)", doc_text, re.MULTILINE)
    assert m
    body = m.group("body")
    doc_values: set[str] = set()
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        first = cells[0]
        m2 = re.match(r"`([^`]+)`", first)
        if m2 and m2.group(1) not in {"Value"}:
            doc_values.add(m2.group(1))
    enum_names = {member.name for member in License}
    assert doc_values == enum_names, (
        f"License enum drift.\n  only-in-doc: {doc_values - enum_names}\n"
        f"  only-in-enum: {enum_names - doc_values}"
    )
