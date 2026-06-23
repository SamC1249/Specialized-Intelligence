#!/usr/bin/env python3
"""End-to-end dry run of the v0 pipeline on synthetic inputs.

Used by the CI e2e job and by `tests/e2e/test_pipeline.py`.

Inputs:
  --out DIR : where to write the manifests (raw_video.jsonl, clip.jsonl,
              shard.jsonl).
Outputs (files): three JSON-Lines manifests in --out.

The script does not touch the network. It builds a synthetic two-video
input set, then runs:
  1. discover stub  -> raw_video.jsonl
  2. license_check  -> drops UNKNOWN
  3. segment        -> clip.jsonl (whole-video splitter)
  4. score          -> phash64 on a synthetic frame
  5. dedup          -> drop duplicates within Hamming 4
  6. contamination_gate -> reject clips inside the eval-set blocklist
  7. curate         -> shard.jsonl with purpose=pretrain

Determinism: given the same code, the manifests are byte-identical
across runs (no wall-clock time in fixed fields except `collected_at`,
which is overridden via env `FAKE_NOW`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Allow running via `python scripts/pipeline_dry_run.py` from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from components.manifest_schema import (  # noqa: E402
    CLIP_SCHEMA,
    RAW_VIDEO_SCHEMA,
    SHARD_SCHEMA,
    validate_row,
)
from components.phash import hamming, phash64  # noqa: E402

PIPELINE_VERSION = "0.0.1"


def _now() -> str:
    return os.environ.get("FAKE_NOW", "2026-06-20T17:30:00Z")


def _video_id(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode()).hexdigest()[:16]


def _clip_id(video_id: str, start_s: float, end_s: float) -> str:
    return hashlib.sha256(f"{video_id}|{start_s}|{end_s}".encode()).hexdigest()[:16]


def _synth_image(seed: int, size: int = 32) -> list[list[float]]:
    """Deterministic gradient-+-offset image; controls phash output."""
    return [[((x + y + seed) % size) / float(size - 1) for x in range(size)] for y in range(size)]


def discover() -> list[dict]:
    """Stub discoverer: emits 3 raw_video rows for the dry run."""
    rows = [
        {
            "canonical_url": "https://commons.wikimedia.org/wiki/File:DryRunA.webm",
            "source": "wikimedia_commons",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "DryRun Author A",
            "title": "Dry Run A",
            "duration_s": 5.0,
            "_seed": 1,  # used downstream for synthetic phash; stripped before write
        },
        {
            "canonical_url": "https://commons.wikimedia.org/wiki/File:DryRunB.webm",
            "source": "wikimedia_commons",
            "license": "CC-BY-SA-4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "DryRun Author B",
            "title": "Dry Run B",
            "duration_s": 7.0,
            "_seed": 200,
        },
        {
            # Will be excluded by license_check.
            "canonical_url": "https://example.com/Unknown.webm",
            "source": "other_open",
            "license": "UNKNOWN",
            "license_url": None,
            "attribution": None,
            "title": "Unknown",
            "duration_s": 9.0,
            "_seed": 7,
        },
    ]
    out = []
    for r in rows:
        seed = r.pop("_seed")
        full = {
            "video_id": _video_id(r["canonical_url"]),
            "source": r["source"],
            "canonical_url": r["canonical_url"],
            "media_url": None,
            "license": r["license"],
            "license_url": r["license_url"],
            "attribution": r["attribution"],
            "title": r["title"],
            "description": None,
            "language": "en",
            "duration_s": r["duration_s"],
            "width": None,
            "height": None,
            "fps": None,
            "bytes": None,
            "sha256": None,
            "collected_at": _now(),
            "pipeline_version": PIPELINE_VERSION,
            "tags": ["cooking"],
            "excluded": False,
            "exclusion_reason": None,
        }
        full["__seed__"] = seed  # internal carry for the dry run
        out.append(full)
    return out


def license_check(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        rr = dict(r)
        if rr["license"] == "UNKNOWN":
            rr["excluded"] = True
            rr["exclusion_reason"] = "license is UNKNOWN (db_structured §3)"
        out.append(rr)
    return out


def segment(rows: list[dict]) -> list[dict]:
    """Whole-video splitter for the dry run (one clip per kept video)."""
    clips: list[dict] = []
    for r in rows:
        if r["excluded"]:
            continue
        start, end = 0.0, float(r["duration_s"])
        clip = {
            "clip_id": _clip_id(r["video_id"], start, end),
            "video_id": r["video_id"],
            "start_s": start,
            "end_s": end,
            "duration_s": end - start,
            "splitter": "whole",
            "caption": None,
            "caption_source": None,
            "phash64": None,
            "dover_score": None,
            "motion_score": None,
            "excluded": False,
            "exclusion_reason": None,
            "__seed__": r["__seed__"],
        }
        clips.append(clip)
    return clips


def score(clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    for c in clips:
        seed = c.pop("__seed__")
        c = dict(c)
        c["phash64"] = phash64(_synth_image(seed))
        c["motion_score"] = 0.5
        c["dover_score"] = 0.7
        out.append(c)
    return out


def dedup(clips: list[dict], threshold: int = 4) -> list[dict]:
    out: list[dict] = []
    seen: list[str] = []
    for c in clips:
        c2 = dict(c)
        h = c2["phash64"]
        if any(hamming(h, s) <= threshold for s in seen):
            c2["excluded"] = True
            c2["exclusion_reason"] = f"near-duplicate within Hamming {threshold}"
        else:
            seen.append(h)
        out.append(c2)
    return out


def contamination_gate(clips: list[dict], blocklist_path: Path | None = None) -> list[dict]:
    """Reject clips whose pHash falls inside the eval-set blocklist (default radius 8)."""
    if blocklist_path is None or not blocklist_path.exists():
        return clips
    # Imported lazily so the script keeps a small import surface.
    from specint.contamination import Blocklist

    bl = Blocklist.load_jsonl(blocklist_path, max_distance=8)
    out: list[dict] = []
    for c in clips:
        c2 = dict(c)
        if not c2["excluded"] and c2.get("phash64") and bl.contains(c2["phash64"]):
            c2["excluded"] = True
            c2["exclusion_reason"] = "matches eval-set blocklist (contamination gate)"
        out.append(c2)
    return out


def curate(clips: list[dict]) -> dict:
    keep_ids = [c["clip_id"] for c in clips if not c["excluded"]]
    return {
        "shard_id": "dryrun_shard_0",
        "clip_ids": keep_ids,
        "purpose": "pretrain",
        "created_at": _now(),
        "notes": "synthetic dry-run shard",
    }


def _strip_internal(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("__")}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(_strip_internal(r), sort_keys=True) + "\n")


def run(out_dir: Path, blocklist_path: Path | None = None) -> None:
    raw = license_check(discover())
    for r in raw:
        validate_row(RAW_VIDEO_SCHEMA, _strip_internal(r))

    clips = score(segment(raw))
    deduped = dedup(clips)
    gated = contamination_gate(deduped, blocklist_path)
    for c in gated:
        validate_row(CLIP_SCHEMA, _strip_internal(c))

    shard = curate(gated)
    validate_row(SHARD_SCHEMA, shard)

    _write_jsonl(out_dir / "raw_video.jsonl", raw)
    _write_jsonl(out_dir / "clip.jsonl", gated)
    _write_jsonl(out_dir / "shard.jsonl", [shard])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument(
        "--blocklist",
        type=Path,
        default=REPO_ROOT / "data" / "blocklists" / "eval_seed.jsonl",
        help="JSONL eval-set blocklist for the contamination gate.",
    )
    args = ap.parse_args()
    run(args.out, args.blocklist if args.blocklist.exists() else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
