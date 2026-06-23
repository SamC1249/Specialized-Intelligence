"""End-to-end test of the v0 pipeline dry run.

Runs scripts/pipeline_dry_run.py twice and asserts:
- All three manifests are produced.
- Output is byte-identical across runs (determinism).
- The shard manifest excludes the UNKNOWN-license input.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.e2e
def test_pipeline_dry_run_is_deterministic_and_correct(tmp_path: Path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    env = os.environ.copy()
    env["FAKE_NOW"] = "2026-06-20T17:30:00Z"

    for out in (out_a, out_b):
        r = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "pipeline_dry_run.py"), "--out", str(out)],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert r.returncode == 0, r.stderr

    for name in ("raw_video.jsonl", "clip.jsonl", "shard.jsonl"):
        a = (out_a / name).read_bytes()
        b = (out_b / name).read_bytes()
        assert a == b, f"{name} not deterministic"

    raw_rows = [json.loads(line) for line in (out_a / "raw_video.jsonl").read_text().splitlines()]
    clip_rows = [json.loads(line) for line in (out_a / "clip.jsonl").read_text().splitlines()]
    shard_rows = [json.loads(line) for line in (out_a / "shard.jsonl").read_text().splitlines()]

    # Three raw videos: two kept, one excluded for UNKNOWN license.
    assert len(raw_rows) == 3
    excluded = [r for r in raw_rows if r["excluded"]]
    assert len(excluded) == 1
    assert excluded[0]["license"] == "UNKNOWN"
    assert "UNKNOWN" in excluded[0]["exclusion_reason"]

    # Two clips emitted (one per kept raw video, "whole" splitter).
    assert len(clip_rows) == 2

    # One shard, exactly the kept clip ids.
    assert len(shard_rows) == 1
    kept_clip_ids = {c["clip_id"] for c in clip_rows if not c["excluded"]}
    assert set(shard_rows[0]["clip_ids"]) == kept_clip_ids
    assert shard_rows[0]["purpose"] == "pretrain"
