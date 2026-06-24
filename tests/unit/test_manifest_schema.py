"""Schema-validation tests for db_structured.md §2."""

from __future__ import annotations

import pytest
from jsonschema import ValidationError

from components.manifest_schema import (
    CLIP_SCHEMA,
    RAW_VIDEO_SCHEMA,
    SHARD_SCHEMA,
    validate_row,
)


def _good_raw_video() -> dict:
    return {
        "video_id": "0123456789abcdef",
        "source": "wikimedia_commons",
        "canonical_url": "https://commons.wikimedia.org/wiki/File:Example.webm",
        "media_url": None,
        "license": "CC-BY-SA-4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": "Some Author",
        "title": "Example",
        "description": None,
        "language": "en",
        "duration_s": 42.0,
        "width": 1280,
        "height": 720,
        "fps": 30.0,
        "bytes": 12345,
        "sha256": "a" * 64,
        "collected_at": "2026-06-20T17:00:00Z",
        "pipeline_version": "0.0.1",
        "tags": ["cooking"],
        "excluded": False,
        "exclusion_reason": None,
    }


def _good_clip() -> dict:
    return {
        "clip_id": "fedcba9876543210",
        "video_id": "0123456789abcdef",
        "start_s": 0.0,
        "end_s": 5.0,
        "duration_s": 5.0,
        "splitter": "pyscenedetect",
        "caption": "a hand chops an onion",
        "caption_source": "vlm:blip2",
        "phash64": "00112233445566ff",
        "dover_score": 0.7,
        "motion_score": 0.42,
        "excluded": False,
        "exclusion_reason": None,
    }


def _good_shard() -> dict:
    return {
        "shard_id": "shard_2026_06_20_a",
        "clip_ids": ["fedcba9876543210"],
        "purpose": "pretrain",
        "created_at": "2026-06-20T17:30:00Z",
        "notes": None,
    }


def test_raw_video_happy_path():
    validate_row(RAW_VIDEO_SCHEMA, _good_raw_video())


def test_clip_happy_path():
    validate_row(CLIP_SCHEMA, _good_clip())


def test_shard_happy_path():
    validate_row(SHARD_SCHEMA, _good_shard())


def test_raw_video_unknown_license_must_be_excluded():
    row = _good_raw_video()
    row["license"] = "UNKNOWN"
    row["excluded"] = False
    with pytest.raises(ValueError, match="UNKNOWN"):
        validate_row(RAW_VIDEO_SCHEMA, row)


def test_raw_video_excluded_requires_reason():
    row = _good_raw_video()
    row["excluded"] = True
    row["exclusion_reason"] = None
    with pytest.raises(ValueError, match="exclusion_reason"):
        validate_row(RAW_VIDEO_SCHEMA, row)


def test_raw_video_rejects_bad_source():
    row = _good_raw_video()
    row["source"] = "youtube"  # explicitly disallowed
    with pytest.raises(ValidationError):
        validate_row(RAW_VIDEO_SCHEMA, row)


def test_clip_rejects_zero_length():
    row = _good_clip()
    row["start_s"] = 5.0
    row["end_s"] = 5.0
    row["duration_s"] = 0.0
    with pytest.raises(ValueError):
        validate_row(CLIP_SCHEMA, row)


def test_clip_rejects_inconsistent_duration():
    row = _good_clip()
    row["duration_s"] = 6.0  # but end_s - start_s == 5.0
    with pytest.raises(ValueError, match="duration_s"):
        validate_row(CLIP_SCHEMA, row)


def test_shard_allows_empty_clip_ids():
    """Updated 2026-06-24: an empty shard is the canonical signal that the
    run produced zero shippable clips (e.g. all candidates collided with
    the eval blocklist). See db_structured.md §2.3."""
    row = _good_shard()
    row["clip_ids"] = []
    validate_row(SHARD_SCHEMA, row)


def test_shard_rejects_malformed_clip_id():
    row = _good_shard()
    row["clip_ids"] = ["not-a-hex-16"]
    with pytest.raises(ValidationError):
        validate_row(SHARD_SCHEMA, row)
