"""Pre-commit hook: every non-underscore module under
`src/specint/sources/` (except `base` and `__init__`) must be listed in
`specint.sources.REGISTRY`. If a new adapter is added but not registered,
the comparison harness silently ignores it — this hook prevents that.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "src" / "specint" / "sources"


def module_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in SOURCES_DIR.glob("*.py"):
        name = path.stem
        if name.startswith("_") or name == "base":
            continue
        slugs.add(name)
    return slugs


def registry_slugs() -> set[str]:
    sys.path.insert(0, str(ROOT / "src"))
    from specint.sources import REGISTRY

    return set(REGISTRY.keys()) | {cls.__module__.rsplit(".", 1)[-1] for cls in REGISTRY.values()}


def main() -> int:
    modules = module_slugs()
    registered = registry_slugs()
    missing = modules - registered
    if missing:
        print(
            "Sources present as modules but missing from specint.sources.REGISTRY: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
