"""Unit tests for scripts/precommit_require_license_field.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "scripts" / "precommit_require_license_field.py"


def _run(paths: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_ok_when_adapter_has_both_fields(tmp_path: Path) -> None:
    f = _write(
        tmp_path / "components" / "sources" / "good.py",
        'LICENSE = "CC-BY-4.0"\nlicense_confidence = 0.95\n',
    )
    r = _run([f])
    assert r.returncode == 0, r.stderr


def test_fails_when_adapter_missing_confidence(tmp_path: Path) -> None:
    f = _write(
        tmp_path / "components" / "sources" / "bad.py",
        'LICENSE = "CC-BY-4.0"\n',
    )
    r = _run([f])
    assert r.returncode == 1
    assert "license_confidence" in r.stderr


def test_ignores_init_files(tmp_path: Path) -> None:
    f = _write(tmp_path / "components" / "sources" / "__init__.py", '"""adapters"""\nlicense = 1\n')
    r = _run([f])
    assert r.returncode == 0


def test_ignores_non_adapter_files(tmp_path: Path) -> None:
    f = _write(tmp_path / "scripts" / "demo.py", 'license = "CC-BY"\n')
    r = _run([f])
    assert r.returncode == 0


def test_ignores_files_without_license_string(tmp_path: Path) -> None:
    f = _write(tmp_path / "components" / "sources" / "neutral.py", "def f():\n    return 1\n")
    r = _run([f])
    assert r.returncode == 0
