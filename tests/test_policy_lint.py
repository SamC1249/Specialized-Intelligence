from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_policy_lint():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "policy_lint_mod", root / "scripts" / "policy_lint.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def policy_lint():
    return _load_policy_lint()


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "reports").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "scripts").mkdir()
    return tmp_path


def test_policy_lint_accepts_clean_repo(tmp_path: Path, policy_lint):
    root = _make_repo(tmp_path)
    (root / "reports" / "ok.json").write_text(
        json.dumps(
            {
                "query": {"terms": ["cooking"], "max_results": 5, "language": None},
                "records": [
                    {
                        "id": "wikimedia:1",
                        "license": "CC-BY",
                        "url": "https://commons.wikimedia.org/1",
                    }
                ],
            }
        )
    )
    (root / "src" / "hello.py").write_text("print('hello')\n")
    assert policy_lint.check_reports(root) == []
    assert policy_lint.check_source_hosts(root) == []


def test_policy_lint_rejects_restricted_license_in_report(tmp_path: Path, policy_lint):
    root = _make_repo(tmp_path)
    (root / "reports" / "bad.json").write_text(
        json.dumps(
            {"records": [{"id": "x", "license": "RESTRICTED", "url": "https://example.org/x"}]}
        )
    )
    problems = policy_lint.check_reports(root)
    assert problems, "expected at least one violation for RESTRICTED license"
    assert any("RESTRICTED" in msg for msg in problems)


def test_policy_lint_allows_unknown_but_flags_random_string(tmp_path: Path, policy_lint):
    root = _make_repo(tmp_path)
    (root / "reports" / "unknown_ok.json").write_text(
        json.dumps({"records": [{"id": "x", "license": "UNKNOWN"}]})
    )
    (root / "reports" / "weird.json").write_text(
        json.dumps({"records": [{"id": "y", "license": "SOMETHING-WEIRD"}]})
    )
    problems = policy_lint.check_reports(root)
    assert not any("UNKNOWN" in msg for msg in problems)
    assert any("SOMETHING-WEIRD" in msg for msg in problems)


def test_policy_lint_rejects_blocked_host_in_source(tmp_path: Path, policy_lint):
    root = _make_repo(tmp_path)
    (root / "src" / "bad.py").write_text('URL = "https://www.youtube.com/watch?v=abc"\n')
    problems = policy_lint.check_source_hosts(root)
    assert any("youtube.com" in msg for msg in problems)


def test_policy_lint_ignores_blocked_host_in_docs(tmp_path: Path, policy_lint):
    root = _make_repo(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("we intentionally block https://www.youtube.com/watch")
    assert policy_lint.check_source_hosts(root) == []


def test_policy_lint_main_returns_zero_on_repo(policy_lint):
    root = Path(__file__).resolve().parents[1]
    rc = policy_lint.main(["--root", str(root), "--check", "all"])
    assert rc == 0
