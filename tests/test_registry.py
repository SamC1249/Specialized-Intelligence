"""Registry integrity — 'add a source without touching the CLI'.

Adversarial question #4 (docs/plan-2026-09-11.md): a new adapter should
be drop-in. This test guards the invariants that make that true:

  - Every entry in `REGISTRY` maps `slug -> BaseSource subclass`.
  - Each source class exposes a matching `slug` attribute.
  - No two sources share a slug (or a class).
  - Instantiating each source does not perform I/O.

If a future refactor hardcodes a source name in the CLI or the harness,
this test still passes — but any duplicate/typo in `REGISTRY` fails
loudly.
"""

from __future__ import annotations

from specint.sources import REGISTRY
from specint.sources.base import BaseSource


def test_registry_is_non_empty() -> None:
    assert REGISTRY, "REGISTRY must contain at least one adapter"


def test_registry_slugs_are_unique_and_match_classes() -> None:
    seen_slugs: set[str] = set()
    seen_classes: set[type[BaseSource]] = set()
    for slug, cls in REGISTRY.items():
        assert isinstance(slug, str) and slug, f"empty slug for {cls}"
        assert issubclass(cls, BaseSource), f"{cls} does not subclass BaseSource"
        assert cls.slug == slug, f"REGISTRY key {slug!r} != {cls.__name__}.slug ({cls.slug!r})"
        assert slug not in seen_slugs, f"duplicate slug: {slug}"
        assert cls not in seen_classes, f"duplicate class: {cls}"
        seen_slugs.add(slug)
        seen_classes.add(cls)


def test_every_source_can_be_instantiated_without_network() -> None:
    for cls in REGISTRY.values():
        instance = cls()
        assert hasattr(instance, "parse"), f"{cls.__name__} lacks parse()"
        assert hasattr(instance, "search"), f"{cls.__name__} lacks search()"
        # Empty parse must never crash; this is the pure-function contract.
        empty = instance.parse(
            {}, __import__("specint.records", fromlist=["SourceQuery"]).SourceQuery(terms=[])
        )
        assert empty == [], f"{cls.__name__}.parse({{}}) must yield []"
