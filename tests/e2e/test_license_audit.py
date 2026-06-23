"""End-to-end: the license-audit script's behaviour on a tiny fixture
corpus.

Two shards live under ``tests/e2e/fixtures``:

* ``clean_shard`` — only CC0 + CC-BY rows. Audit must pass.
* ``dirty_shard`` — contains CC-BY-NC + UNKNOWN. Audit must fail and
  must identify the offending licenses by name.

The CI runs ``audit_licenses.py --dry-run`` on the *combined* corpus; in
that case it must fail (because the dirty shard is present).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "audit_licenses.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )


def test_audit_passes_on_clean_shard() -> None:
    fixture = ROOT / "tests" / "e2e" / "fixtures" / "clean_shard"
    res = _run(["--root", str(fixture)])
    assert res.returncode == 0, res.stderr
    assert "license audit OK" in res.stdout


def test_audit_fails_on_dirty_shard() -> None:
    fixture = ROOT / "tests" / "e2e" / "fixtures" / "dirty_shard"
    res = _run(["--root", str(fixture)])
    assert res.returncode == 1
    assert "CC_BY_NC" in res.stderr
    assert "UNKNOWN" in res.stderr


def test_dry_run_walks_the_full_fixture_tree() -> None:
    """--dry-run audits everything under tests/e2e/fixtures.

    Since the tree includes the dirty shard, the audit must fail.
    """
    res = _run(["--dry-run"])
    assert res.returncode == 1
    assert "license audit FAILED" in res.stderr
