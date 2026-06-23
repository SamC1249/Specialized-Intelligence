"""End-to-end: docs-sync script behaviour.

Runs the same script CI runs and asserts it exits 0 against this repo
(i.e. the bootstrap is complete).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "check_docs_sync.py"


def test_docs_sync_passes_on_current_repo() -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert res.returncode == 0, f"stdout={res.stdout!r} stderr={res.stderr!r}"
