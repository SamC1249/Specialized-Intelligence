"""End-to-end test for the eval-set blocklist path of the dry-run pipeline.

We run the dry-run pipeline twice:

  (a) without `--eval-blocklist`: baseline behavior (existing test
      covers correctness).
  (b) with a `--eval-blocklist` whose entries are the *exact* pHashes
      the synthetic discoverer emits.

In (b), every kept clip must end up `excluded == true` with reason
`eval_blocklist_hit`, the shard must contain zero clip_ids.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _run_baseline(tmp_path: Path) -> Path:
    """Run the pipeline without a blocklist to learn the pHashes it emits."""
    out = tmp_path / "baseline"
    env = os.environ.copy()
    env["FAKE_NOW"] = "2026-06-24T17:00:00Z"
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "pipeline_dry_run.py"), "--out", str(out)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    return out


@pytest.mark.e2e
def test_blocklist_excludes_all_clips_when_seeded_with_their_phashes(tmp_path: Path) -> None:
    baseline = _run_baseline(tmp_path)
    clips = [json.loads(line) for line in (baseline / "clip.jsonl").read_text().splitlines()]
    assert len(clips) >= 1
    blocklist_path = tmp_path / "blocklist.jsonl"
    with blocklist_path.open("w") as fh:
        for c in clips:
            fh.write(json.dumps({"phash64": c["phash64"], "source": "test_seed"}) + "\n")

    out = tmp_path / "with_blocklist"
    env = os.environ.copy()
    env["FAKE_NOW"] = "2026-06-24T17:00:00Z"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "pipeline_dry_run.py"),
            "--out",
            str(out),
            "--eval-blocklist",
            str(blocklist_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 0, r.stderr

    clip_rows = [json.loads(line) for line in (out / "clip.jsonl").read_text().splitlines()]
    shard_rows = [json.loads(line) for line in (out / "shard.jsonl").read_text().splitlines()]

    assert clip_rows, "expected at least one clip row"
    for c in clip_rows:
        assert c["excluded"] is True
        assert c["exclusion_reason"] is not None
        assert "eval_blocklist_hit" in c["exclusion_reason"]

    assert len(shard_rows) == 1
    assert shard_rows[0]["clip_ids"] == []


@pytest.mark.e2e
def test_blocklist_with_unrelated_hashes_does_not_exclude(tmp_path: Path) -> None:
    """A blocklist that doesn't match any clip should leave the shard intact."""
    baseline = _run_baseline(tmp_path)
    baseline_clips = [
        json.loads(line) for line in (baseline / "clip.jsonl").read_text().splitlines()
    ]
    kept_baseline = [c for c in baseline_clips if not c["excluded"]]
    assert kept_baseline, "expected at least one non-excluded baseline clip"

    blocklist_path = tmp_path / "blocklist.jsonl"
    # 16-char hex that we choose to differ from all baseline pHashes.
    # If by astronomical coincidence it collides, we'll pick another.
    unrelated = "0123456789abcdef"
    baseline_phashes = {c["phash64"] for c in baseline_clips}
    if unrelated in baseline_phashes:
        unrelated = "fedcba9876543210"
    blocklist_path.write_text(json.dumps({"phash64": unrelated}) + "\n")

    out = tmp_path / "unrelated"
    env = os.environ.copy()
    env["FAKE_NOW"] = "2026-06-24T17:00:00Z"
    r = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "pipeline_dry_run.py"),
            "--out",
            str(out),
            "--eval-blocklist",
            str(blocklist_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    clip_rows = [json.loads(line) for line in (out / "clip.jsonl").read_text().splitlines()]
    shard_rows = [json.loads(line) for line in (out / "shard.jsonl").read_text().splitlines()]
    kept_with_blocklist = [c for c in clip_rows if not c["excluded"]]
    assert len(kept_with_blocklist) == len(kept_baseline)
    assert shard_rows[0]["clip_ids"] == [c["clip_id"] for c in kept_with_blocklist]
