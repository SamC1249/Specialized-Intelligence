"""Unit tests for the `Stage` contract.

The whole point of the pipeline is reproducibility, so the contract that
*every* stage must emit a manifest with name + version + git sha + row
counts has to be tested centrally — not left to each subclass.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specialized_intelligence.pipeline import Stage, StageManifest


class _NoopStage(Stage):
    name = "test.noop"
    version = "0.0.1"

    def run(self, input_dir: Path, output_dir: Path) -> StageManifest:
        started = datetime.now(tz=UTC)
        return self._write_manifest(
            output_dir,
            started_at=started,
            rows_in=3,
            rows_out=3,
            extra={"license_norm_counts": {"CC_BY": 2, "CC0": 1}},
        )


def test_stage_without_name_raises() -> None:
    class BadStage(Stage):
        version = "0.0.1"

        def run(self, input_dir: Path, output_dir: Path) -> StageManifest:
            raise NotImplementedError

    with pytest.raises(TypeError, match="must set class attr `name`"):
        BadStage()


def test_stage_without_version_raises() -> None:
    class BadStage(Stage):
        name = "x"

        def run(self, input_dir: Path, output_dir: Path) -> StageManifest:
            raise NotImplementedError

    with pytest.raises(TypeError, match="must set class attr `version`"):
        BadStage()


def test_stage_writes_atomic_manifest(tmp_path: Path) -> None:
    stage = _NoopStage(git_sha="abc1234")
    out = tmp_path / "out"
    manifest = stage.run(tmp_path / "in", out)

    final = out / "_MANIFEST.json"
    assert final.exists()
    assert not (out / "_MANIFEST.json.tmp").exists(), "tmp file must be renamed"

    payload = json.loads(final.read_text())
    assert payload["stage_name"] == "test.noop"
    assert payload["stage_version"] == "0.0.1"
    assert payload["git_sha"] == "abc1234"
    assert payload["rows_in"] == 3
    assert payload["rows_out"] == 3
    assert payload["extra"]["license_norm_counts"]["CC_BY"] == 2
    assert manifest.stage_name == "test.noop"


def test_manifest_is_deterministic_order() -> None:
    m = StageManifest(
        stage_name="s",
        stage_version="v",
        git_sha="g",
        started_at="2026-06-23T00:00:00+00:00",
        finished_at="2026-06-23T00:00:01+00:00",
        rows_in=0,
        rows_out=0,
    )
    payload = json.loads(m.to_json())
    assert list(payload.keys()) == sorted(payload.keys()), "keys must be sorted"
