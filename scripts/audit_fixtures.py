#!/usr/bin/env python3
"""Fast pre-commit check: fixtures under tests/fixtures/ must stay clean.

Runs in <1s. Complements the pytest suite by catching corruption early
(before any Python import is even attempted).

Checks:
  1. Every *.json fixture parses as JSON.
  2. Every fixture directory name matches a registered source slug
     (`src/specint/sources/__init__.py::REGISTRY`).
  3. Every *.html fixture looks structurally like HTML.

Non-zero exit means the pre-commit hook fails. This intentionally
does NOT import Pydantic models — that's what pytest is for. Keep this
script dependency-free so pre-commit stays instant.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SOURCES_INIT = ROOT / "src" / "specint" / "sources" / "__init__.py"

REGISTRY_KEY_PATTERN = re.compile(r'"([a-z_][a-z0-9_]*)"\s*:\s*[A-Z]\w*Source')


def registered_slugs() -> set[str]:
    text = SOURCES_INIT.read_text()
    return set(REGISTRY_KEY_PATTERN.findall(text))


def main() -> int:
    errors: list[str] = []

    if not FIXTURES.exists():
        print(f"no fixtures directory at {FIXTURES}", file=sys.stderr)
        return 1

    slugs = registered_slugs()
    if not slugs:
        errors.append(
            f"could not parse any source slugs out of {SOURCES_INIT}. REGISTRY layout changed?"
        )

    for path in sorted(FIXTURES.rglob("*.json")):
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON fixture: {path.relative_to(ROOT)}: {exc}")

    for path in sorted(FIXTURES.rglob("*.html")):
        text = path.read_text().lower()
        if "<html" not in text and "<!doctype" not in text:
            errors.append(f"HTML fixture missing <html> / <!doctype>: {path.relative_to(ROOT)}")
        if len(text) < 200:
            errors.append(f"HTML fixture suspiciously small (<200 chars): {path.relative_to(ROOT)}")

    for child in sorted(FIXTURES.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if child.name not in slugs:
            errors.append(
                f"fixtures/{child.name}/ has no matching REGISTRY entry in "
                f"{SOURCES_INIT.relative_to(ROOT)}"
            )

    if errors:
        for e in errors:
            print(f"[audit_fixtures] {e}", file=sys.stderr)
        return 1

    print(f"[audit_fixtures] ok — {len(list(FIXTURES.rglob('*')))} fixture entries clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
