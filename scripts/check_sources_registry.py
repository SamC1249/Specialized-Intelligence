#!/usr/bin/env python3
"""Registry-consistency check.

Walks every module in ``src/specint/sources/`` and asserts that every
concrete ``BaseSource`` subclass is registered in
``specint.sources.REGISTRY``. A missing registration would silently drop
the source from the comparison harness and the CLI.

Also asserts the inverse: every slug in ``REGISTRY`` resolves to an
importable ``BaseSource`` subclass.

Runs offline. Suitable as a pre-commit hook.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys

from specint.sources import REGISTRY
from specint.sources.base import BaseSource


def _concrete_subclasses() -> dict[str, type[BaseSource]]:
    package = importlib.import_module("specint.sources")
    found: dict[str, type[BaseSource]] = {}
    assert package.__file__ is not None
    for _finder, name, _is_pkg in pkgutil.iter_modules(package.__path__):
        if name in {"base", "__init__"}:
            continue
        mod = importlib.import_module(f"specint.sources.{name}")
        for _cls_name, cls in inspect.getmembers(mod, inspect.isclass):
            if (
                cls is BaseSource
                or not issubclass(cls, BaseSource)
                or inspect.isabstract(cls)
                or cls.__module__ != mod.__name__
            ):
                continue
            slug = getattr(cls, "slug", "") or name
            found[slug] = cls
    return found


def main() -> int:
    discovered = _concrete_subclasses()
    registered = dict(REGISTRY)

    violations: list[str] = []

    missing = sorted(set(discovered) - set(registered))
    for slug in missing:
        cls = discovered[slug]
        violations.append(
            f"source class {cls.__module__}.{cls.__name__} (slug={slug!r}) "
            f"is defined but not in specint.sources.REGISTRY"
        )

    stale = sorted(set(registered) - set(discovered))
    for slug in stale:
        violations.append(
            f"REGISTRY has slug {slug!r} but no corresponding concrete "
            "BaseSource subclass was discovered under src/specint/sources/"
        )

    for slug, cls in sorted(registered.items()):
        reg_slug = getattr(cls, "slug", "")
        if reg_slug and reg_slug != slug:
            violations.append(
                f"REGISTRY key {slug!r} does not match class slug "
                f"attribute {reg_slug!r} on {cls.__name__}"
            )

    if violations:
        print("sources-registry: FAIL", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    print(f"sources-registry: OK ({len(registered)} sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
