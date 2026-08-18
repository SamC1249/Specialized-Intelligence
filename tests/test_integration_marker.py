"""Enforce the offline-tests invariant.

Every registered source must expose a `search()` callable, and no test
file may exercise it without carrying the `integration` marker.
"""

from __future__ import annotations

import ast
from pathlib import Path

from specint.sources import REGISTRY

TEST_ROOT = Path(__file__).parent


def test_every_source_exposes_search_and_parse():
    for slug, cls in REGISTRY.items():
        assert callable(getattr(cls, "search", None)), f"{slug} missing search()"
        assert callable(getattr(cls, "parse", None)), f"{slug} missing parse()"


def _calls_search_method(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "search"
        ):
            return True
    return False


def _uses_integration_marker(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "integration":
            return True
    return False


def test_no_offline_test_calls_search():
    for path in TEST_ROOT.rglob("test_*.py"):
        if "fixtures" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if _calls_search_method(tree):
            assert _uses_integration_marker(tree), (
                f"{path.name} calls .search() but is missing @pytest.mark.integration"
            )
