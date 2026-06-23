# db_structured.md

This is the **single source of truth** for every data table, file format,
pipeline stage, and external API that the project reads or writes. If the
code disagrees with this document, the document wins and the code is wrong.

Every agent must update this file in the same PR that introduces, renames,
or removes any of the entities below.

---

## 1. External data sources

| ID            | Kind                | Endpoint / Base URL                         | Auth          | License posture                                  | Notes                                                                 |
| ------------- | ------------------- | ------------------------------------------- | ------------- | ------------------------------------------------ | --------------------------------------------------------------------- |
| `yt_cc_api`   | REST                | `https://www.googleapis.com/youtube/v3`     | API key       | CC-BY filter via `videoLicense=creativeCommon`   | 10k units/day; we **only** request `videoLicense=creativeCommon`.     |
| `vimeo_cc`    | REST                | `https://api.vimeo.com`                     | OAuth token   | `filter=CC` (six CC variants + CC0)              | ~792k CC videos as of 2026-06.                                        |
| `peertube`    | Federated REST      | per-instance, listed in `configs/peertube_instances.yaml` | none / per-instance | mixed; we filter to CC / public-domain only      | discovery via Search API of every known instance.                     |
| `archive_org` | REST + S3-like      | `https://archive.org/advancedsearch.php`    | none          | public-domain / CC                               | cookery shows, cooking demos, public-TV cooking.                      |
| `wikimedia`   | REST                | `https://commons.wikimedia.org/w/api.php`   | none          | CC-BY-SA / CC0                                   | small but high-quality, well-labelled.                                |
| `hf_datasets` | Python              | `datasets` library                          | optional HF token | per-dataset                                  | proxy for already-curated corpora (YouTube-Commons, EPIC-KITCHENS, OmniWorld). |

We never call any source not listed here. Adding one requires a new row plus
a license-audit note in `docs/artifacts/`.

## 2. Pipeline stages and their I/O

The pipeline is a DAG; each stage reads and writes typed records. All records
live in Parquet on disk, partitioned by `source_id` and `ingest_date`.

### 2.1 `discover`

- **In:** source config (`configs/sources/*.yaml`)
- **Out:** `discovered_videos` table

```
discovered_videos (one row per candidate video)
  video_uri:     str           # canonical URI, e.g. "youtube:dQw4w9WgXcQ"
  source_id:     str           # one of the IDs in section 1
  title:         str
  duration_s:    float | None
  upload_date:   date | None
  license_tag:   str           # raw license string from source
  license_norm:  enum          # one of: CC0, CC_BY, CC_BY_SA, CC_BY_NC*, PD, UNKNOWN
  channel_id:    str | None
  raw_metadata:  json          # full payload from source (for provenance)
  discovered_at: timestamp
```

### 2.2 `acquire`

- **In:** `discovered_videos` filtered to `license_norm in {CC0, CC_BY, CC_BY_SA, PD}`
- **Out:** `acquired_videos` table + raw blobs on disk **only** when license permits redistribution; otherwise we store **manifest-only** (video URI + checksum + timestamp).

```
acquired_videos
  video_uri:      str                 # FK -> discovered_videos.video_uri
  storage_mode:   enum                # FULL_BYTES | MANIFEST_ONLY
  local_path:     str | None          # set iff storage_mode == FULL_BYTES
  sha256:         str | None
  width:          int
  height:         int
  fps:            float
  audio_codec:    str | None
  has_asr:        bool
  asr_path:       str | None          # WebVTT or JSON
  acquired_at:    timestamp
  license_norm:   enum                # carried forward, never re-derived
```

### 2.3 `curate.clip`

Splits long videos into shot-aware clips (Cosmos-style: scene change OR
fixed-stride fallback). One row per clip.

```
clips
  clip_id:       str            # uuid
  video_uri:     str            # FK
  start_s:       float
  end_s:         float
  duration_s:    float
  shot_score:    float          # confidence of scene-change boundary
  width:         int
  height:        int
  fps:           float
  storage_mode:  enum
  local_path:    str | None
```

### 2.4 `curate.filter`

Drops clips that fail any of: motion, aesthetic, OCR-text-density,
content-type classifier (animation, talking-head). Boolean columns appended.

```
clip_filters (joined onto clips by clip_id)
  motion_score:        float
  aesthetic_score:     float
  text_density:        float           # fraction of frame area that is OCR text
  is_animation:        bool
  is_static_slideshow: bool
  passed:              bool
  failed_reason:       str | None
```

### 2.5 `curate.embed`

```
clip_embeddings
  clip_id:     str
  model:       str             # "cosmos-embed1-224p" by default
  embedding:   float32[D]      # D in {1024, 1408, ...} depending on model
```

### 2.6 `curate.dedup`

```
clip_dedup
  clip_id:        str
  cluster_id:     int
  is_canonical:   bool          # true for the kept clip in a cluster
  nearest_id:     str | None
  nearest_sim:    float | None
```

### 2.7 `annotate.caption`

```
clip_captions
  clip_id:       str
  caption_short: str            # ≤ 24 tokens
  caption_long:  str            # ≤ 256 tokens, structured procedural step
  captioner:     str            # model id + version
  asr_aligned:   bool
```

### 2.8 `annotate.procedural`

DenseStep2M-style structured steps + recipe grounding.

```
procedural_steps
  clip_id:       str
  step_index:    int
  verb:          str            # normalized to a closed verb vocab
  noun:          str            # normalized to a closed noun vocab (ingredients/tools)
  object_state_before: str | None
  object_state_after:  str | None
  recipe_id:     str | None     # FK to recipes (from wikihow / wholefoods / open-recipe-db)
```

### 2.9 `eval.*`

Eval outputs live under `eval_runs/<benchmark>/<run_id>/` as Parquet plus
a `summary.json`. Schema is defined per benchmark inside
`src/specialized_intelligence/eval/<benchmark>.py`.

## 3. On-disk layout

```
data/
├── raw/                          # FULL_BYTES videos, partitioned by source/date
├── clips/                        # curated clip mp4s, partitioned by clip_id[:2]
├── meta/
│   ├── discovered/               # parquet
│   ├── acquired/
│   ├── clips/
│   ├── filters/
│   ├── embeddings/
│   ├── dedup/
│   └── captions/
└── eval_runs/
```

`data/` is **never** committed. CI enforces this via `.gitignore` plus a
size-budget check on PRs.

## 4. Pipeline contracts (the only ones the CI checks)

- Every stage takes `--input <parquet-dir>` and `--output <parquet-dir>`.
- Every stage is **idempotent** on `(clip_id, stage_version)`.
- Every stage emits a `_MANIFEST.json` with `stage_version`, `git_sha`,
  `started_at`, `finished_at`, `rows_in`, `rows_out`.
- License posture is carried in every row; a stage that drops it fails CI.

## 5. Versioning

`stage_version` is bumped any time the *output schema* or the *semantics*
of a stage changes. The CI runs the e2e test against the **current** stage
versions on every PR.

## 6. Privacy

We never store faces of identifiable non-public individuals beyond what is
already present in the source video. If a future stage adds face detection,
its row schema must include `face_blurred: bool` and CI must enforce that
all `FULL_BYTES` clips with detected faces are blurred before they leave
the pipeline.
