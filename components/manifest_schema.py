"""JSON schema definitions for the manifests defined in db_structured.md.

This module is the *executable* version of db_structured.md §2.

Inputs / outputs:
  - `RAW_VIDEO_SCHEMA`, `CLIP_SCHEMA`, `SHARD_SCHEMA` are dicts (JSON
    Schema Draft 2020-12).
  - `validate_row(schema, row) -> None` raises `jsonschema.ValidationError`
    if `row` is invalid.

Keep this file in lockstep with db_structured.md. Bumping a field here
*requires* bumping `pipeline_version` in any collector that emits the
schema.
"""

from __future__ import annotations

from typing import Any

import jsonschema

ALLOWED_SOURCES = [
    "wikimedia_commons",
    "internet_archive",
    "vimeo_cc",
    "flickr_pd",
    "gov_open",
    "cc_by",
    "cc_by_sa",
    "cc0",
    "pd_mark",
    "other_open",
]

ALLOWED_LICENSES = [
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "PUBLIC-DOMAIN",
    "OTHER-OPEN",
    "UNKNOWN",
]

ALLOWED_SPLITTERS = [
    "pyscenedetect",
    "transnet_v2",
    "manual",
    "whole",
]

ALLOWED_PURPOSES = ["pretrain", "eval", "probe", "held_out"]


RAW_VIDEO_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "raw_video",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "video_id",
        "source",
        "canonical_url",
        "license",
        "collected_at",
        "pipeline_version",
        "excluded",
    ],
    "properties": {
        "video_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
        "source": {"type": "string", "enum": ALLOWED_SOURCES},
        "canonical_url": {"type": "string", "format": "uri"},
        "media_url": {"type": ["string", "null"], "format": "uri"},
        "license": {"type": "string", "enum": ALLOWED_LICENSES},
        "license_url": {"type": ["string", "null"]},
        "attribution": {"type": ["string", "null"]},
        "title": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "language": {"type": ["string", "null"]},
        "duration_s": {"type": ["number", "null"], "minimum": 0},
        "width": {"type": ["integer", "null"], "minimum": 0},
        "height": {"type": ["integer", "null"], "minimum": 0},
        "fps": {"type": ["number", "null"], "minimum": 0},
        "bytes": {"type": ["integer", "null"], "minimum": 0},
        "sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
        "collected_at": {"type": "string"},
        "pipeline_version": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "excluded": {"type": "boolean"},
        "exclusion_reason": {"type": ["string", "null"]},
    },
}


CLIP_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "clip",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "clip_id",
        "video_id",
        "start_s",
        "end_s",
        "duration_s",
        "splitter",
        "excluded",
    ],
    "properties": {
        "clip_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
        "video_id": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
        "start_s": {"type": "number", "minimum": 0},
        "end_s": {"type": "number", "minimum": 0},
        "duration_s": {"type": "number", "minimum": 0},
        "splitter": {"type": "string", "enum": ALLOWED_SPLITTERS},
        "caption": {"type": ["string", "null"]},
        "caption_source": {
            "type": ["string", "null"],
            # `vlm:<model>` is allowed via pattern below.
        },
        "phash64": {
            "type": ["string", "null"],
            "pattern": "^[0-9a-f]{16}$",
        },
        "dover_score": {"type": ["number", "null"]},
        "motion_score": {"type": ["number", "null"]},
        "excluded": {"type": "boolean"},
        "exclusion_reason": {"type": ["string", "null"]},
    },
}


SHARD_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "shard",
    "type": "object",
    "additionalProperties": False,
    "required": ["shard_id", "clip_ids", "purpose", "created_at"],
    "properties": {
        "shard_id": {"type": "string"},
        "clip_ids": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[0-9a-f]{16}$"},
            "minItems": 0,
        },
        "purpose": {"type": "string", "enum": ALLOWED_PURPOSES},
        "created_at": {"type": "string"},
        "notes": {"type": ["string", "null"]},
    },
}


SCHEMAS_BY_NAME: dict[str, dict[str, Any]] = {
    "raw_video": RAW_VIDEO_SCHEMA,
    "clip": CLIP_SCHEMA,
    "shard": SHARD_SCHEMA,
}


def validate_row(schema: dict[str, Any], row: dict[str, Any]) -> None:
    """Validate one manifest row against `schema`.

    Inputs:
      schema: a JSON Schema dict (one of the constants above).
      row: a dict representing a single JSON-Lines row.

    Raises:
      jsonschema.ValidationError on schema mismatch.
      ValueError on cross-field invariants (e.g. end_s <= start_s).
    """
    jsonschema.validate(instance=row, schema=schema)
    if schema is CLIP_SCHEMA:
        if row["end_s"] <= row["start_s"]:
            raise ValueError("clip: end_s must be > start_s")
        # duration_s must be consistent within a small tolerance
        delta = abs((row["end_s"] - row["start_s"]) - row["duration_s"])
        if delta > 1e-3:
            raise ValueError("clip: duration_s inconsistent with end_s - start_s")
    if schema is RAW_VIDEO_SCHEMA:
        if row["excluded"] and not row.get("exclusion_reason"):
            raise ValueError("raw_video: excluded=true requires exclusion_reason")
        if row["license"] == "UNKNOWN" and not row["excluded"]:
            raise ValueError("raw_video: license=UNKNOWN must be excluded (db_structured §3)")
