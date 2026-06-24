"""Tests for ``scripts/precommit_forbid_youtube.py`` and ``scripts/manifest_lint.py``."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_forbid_youtube_passes_on_clean_files(tmp_path: Path):
    from precommit_forbid_youtube import check_files

    clean = tmp_path / "clean.py"
    clean.write_text("print('hello')\n")
    assert check_files([str(clean)]) == 0


def test_forbid_youtube_fails_when_url_present(tmp_path: Path):
    from precommit_forbid_youtube import check_files

    # Build the URL via concatenation so this very test file does not trigger
    # the hook when it scans the repo (see scripts/precommit_forbid_youtube.py).
    forbidden = "https://www." + "you" + "tube.com/watch?v=xxx"
    bad = tmp_path / "bad.py"
    bad.write_text(f"URL = '{forbidden}'\n")
    assert check_files([str(bad)]) == 1


def test_forbid_youtube_allows_docs_dir(tmp_path: Path, monkeypatch):
    from precommit_forbid_youtube import check_files

    forbidden = "https://" + "you" + "tube.com/watch?v=xxx"
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "note.md").write_text(f"Background reading: {forbidden}")

    monkeypatch.chdir(tmp_path)
    # File is passed as a docs-prefixed relative path: the hook must skip it.
    assert check_files(["docs/note.md"]) == 0


def test_manifest_lint_passes_on_valid_jsonl(tmp_path: Path):
    from manifest_lint import main

    manifest = tmp_path / "ok.jsonl"
    payload = {
        "id": "wikimedia:1",
        "source": "wikimedia",
        "source_native_id": "1",
        "url": "https://commons.wikimedia.org/wiki/File:Test.webm",
        "title": "Test",
        "license": "CC0",
        "license_confidence": 1.0,
        "provenance": {
            "extractor": "specint.sources.wikimedia",
            "extractor_git": "dev",
            "fetched_at": "2026-06-24T00:00:00Z",
            "query": "terms=cooking;max=25;lang=",
        },
    }
    manifest.write_text(json.dumps(payload) + "\n")
    assert main([str(manifest)]) == 0


def test_manifest_lint_fails_on_schema_error(tmp_path: Path, capsys):
    from manifest_lint import main

    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"id": "x"}) + "\n")  # missing required fields
    rc = main([str(bad)])
    assert rc == 1


def test_pipeline_dry_run_cli_runs(tmp_path: Path):
    """Smoke test the CLI entry point end-to-end."""
    manifest = tmp_path / "m.jsonl"
    report = tmp_path / "r.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "pipeline_dry_run.py"),
            "--fixtures",
            str(REPO_ROOT / "tests" / "fixtures"),
            "--manifest",
            str(manifest),
            "--report",
            str(report),
        ],
        check=False,
    ).returncode
    assert rc == 0
    assert manifest.exists() and manifest.read_text().strip()
    assert report.exists() and report.read_text().strip()
