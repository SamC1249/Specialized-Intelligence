"""CI manifest-lint job: every *.jsonl file under data/manifests/ must
schema-validate against the appropriate manifest schema.

Resolution rule: file basename (without .jsonl) must match a key in
`SCHEMAS_BY_NAME`. If no manifests exist yet, the test is a no-op.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from components.manifest_schema import SCHEMAS_BY_NAME, validate_row

REPO = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO / "data" / "manifests"


@pytest.mark.e2e
def test_all_committed_manifests_validate():
    if not MANIFEST_DIR.exists():
        pytest.skip("no manifests committed yet")
    files = list(MANIFEST_DIR.rglob("*.jsonl"))
    if not files:
        pytest.skip("no manifests committed yet")
    for fp in files:
        name = fp.stem
        schema = SCHEMAS_BY_NAME.get(name)
        assert schema is not None, f"no schema registered for {fp.name}"
        for i, line in enumerate(fp.read_text().splitlines(), start=1):
            row = json.loads(line)
            try:
                validate_row(schema, row)
            except Exception as e:
                raise AssertionError(f"{fp}:{i}: {e}") from e
