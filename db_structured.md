# db_structured.md — Single source of truth for data, schemas, and APIs

This file is canonical. **Update it before** writing or changing code that
reads or writes any of these structures. If you cannot describe the input
type, output type, and units of a function, do not implement it; document
the question first.

## 1. Conceptual model

We collect video *references* (URL + license + provenance), enrich them
into *clips* (semantically segmented spans), and finally curate them into
*shards* (downstream-ready manifests). We do **not** host raw video bytes;
we host hashes, references, and derived features.

```
source ──► raw_video ──► clip ──► clip_features ──► shard
                  │           │                    │
                  └ manifest ─┴── provenance ──────┘
```

## 2. JSON Lines manifest schemas (canonical)

All manifests are newline-delimited JSON. Field names are `snake_case`. All
times are ISO-8601 UTC. All durations are in **seconds (float)**. All
positions are in **seconds from start of source video**. All sizes are in
**bytes (int)**.

### 2.1 `raw_video.jsonl`

One row per source video reference.

| field              | type           | units / notes                                                                 |
|--------------------|----------------|-------------------------------------------------------------------------------|
| `video_id`         | str            | Stable internal id (sha256 of canonical url, hex, 16 chars)                   |
| `source`           | enum str       | One of: `wikimedia_commons`, `internet_archive`, `vimeo_cc`, `flickr_pd`, `gov_open`, `cc_by`, `cc_by_sa`, `cc0`, `pd_mark`, `other_open`. **Never** raw `youtube`. |
| `canonical_url`    | str            | HTTPS URL to the source page (not the media file)                             |
| `media_url`        | str \| null    | Direct media URL if license permits download                                  |
| `license`          | enum str       | SPDX-style: `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `PUBLIC-DOMAIN`, `OTHER-OPEN`, `UNKNOWN` |
| `license_url`      | str \| null    |                                                                               |
| `attribution`      | str \| null    | Author / uploader credit string                                               |
| `title`            | str \| null    |                                                                               |
| `description`      | str \| null    |                                                                               |
| `language`         | str \| null    | BCP-47 (e.g. `en`, `ja`)                                                      |
| `duration_s`       | float \| null  | seconds                                                                       |
| `width`            | int \| null    | pixels                                                                        |
| `height`           | int \| null    | pixels                                                                        |
| `fps`              | float \| null  | frames per second                                                             |
| `bytes`            | int \| null    | media size                                                                    |
| `sha256`           | str \| null    | hex digest of the media file (if downloaded)                                  |
| `collected_at`     | str            | ISO-8601 UTC                                                                  |
| `pipeline_version` | str            | semver of the collector                                                       |
| `tags`             | list[str]      | freeform; recommended: domain tags like `cooking`, `recipe`, `egocentric`     |
| `excluded`         | bool           | true if filtered out                                                          |
| `exclusion_reason` | str \| null    | required when `excluded == true`                                              |

### 2.2 `clip.jsonl`

One row per semantically coherent clip cut from a `raw_video`.

| field            | type        | units / notes                                                              |
|------------------|-------------|----------------------------------------------------------------------------|
| `clip_id`        | str         | sha256(`video_id` + start + end), 16 hex chars                             |
| `video_id`       | str         | FK to `raw_video.video_id`                                                 |
| `start_s`        | float       | seconds from start of source                                               |
| `end_s`          | float       | seconds; must be > `start_s`                                               |
| `duration_s`     | float       | == `end_s` - `start_s`                                                     |
| `splitter`       | enum str    | `pyscenedetect`, `transnet_v2`, `manual`, `whole`                          |
| `caption`        | str \| null | machine or human caption                                                   |
| `caption_source` | enum str    | `human`, `asr`, `vlm:<model>`, `none`                                      |
| `phash64`        | str \| null | 64-bit DCT perceptual hash, hex                                            |
| `dover_score`    | float \| null | aesthetic quality score; range model-dependent                          |
| `motion_score`   | float \| null | mean optical-flow magnitude per frame, normalized                        |
| `excluded`       | bool        |                                                                            |
| `exclusion_reason` | str \| null |                                                                          |

### 2.3 `shard.jsonl`

A curated subset for downstream training/eval. Pure pointers + metadata.

| field           | type        |
|-----------------|-------------|
| `shard_id`      | str         |
| `clip_ids`      | list[str]   | may be empty; an empty shard is the canonical signal "this run produced zero shippable clips for this purpose" (e.g. all candidates collided with the eval blocklist) |
| `purpose`       | enum str    | one of `pretrain`, `eval`, `probe`, `held_out` |
| `created_at`    | str         |
| `notes`         | str \| null |

## 3. Reserved enum values

- **`source`**: see 2.1. New values added only via PR with an entry in
  `docs/artifacts/legal-landscape.md` documenting why the source is safe.
- **`license`**: SPDX-style strings. `UNKNOWN` always implies `excluded == true`.
- **`splitter`**: registered in `components/splitters/__init__.py`.

## 4. Function-level contract template

Every public function in `components/` and `scripts/` must declare:

```python
def fn(...):
    """
    Inputs:
      x (np.ndarray, shape [T, H, W, 3], dtype uint8, RGB, frames-per-second f)
    Outputs:
      y (np.ndarray, shape [T], dtype float32, range [0, 1], "motion magnitude")
    Side effects: none / writes to ...
    Raises: ValueError if T < 2.
    """
```

If you cannot fill this in, the function is not ready to merge.

## 5. Open questions (track here, resolve in `docs/plan/`)

- Do we deduplicate by phash64 alone, or do we also embed-match (CLIP/V-JEPA)
  for re-encoded duplicates? *(see `docs/plan/2026-06-20.md`)*
- What is the right "world-model utility score" — a learned predictor, an
  ablation suite, or a proxy like motion + scene diversity?
- How do we handle uploader-level dedup (same person uploading the same
  recipe twice)?

## 6. Versioning

This file is versioned alongside code. Bumping any schema field requires a
SemVer minor bump in `pipeline_version` for collectors and a migration
note here.
