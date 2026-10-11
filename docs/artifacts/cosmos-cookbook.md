# NVIDIA Cosmos — video data curation cookbook

- Source: *Cosmos Cookbook — Data Curation Overview* (NVIDIA, 2025).
- URL: <https://nvidia-cosmos.github.io/cosmos-cookbook/core_concepts/data_curation/overview.html>

## What it is

The Cosmos world-model team publishes an explicit seven-stage video
curation recipe:

1. **Shot-aware splitting** — scene detection; drop clips < 5 s, split
   long ones into 5–60 s segments.
2. **Transcoding** — normalise codec/container/resolution.
3. **Caption generation** — VLM-based captions per clip.
4. **Filtering** (a cascade):
   - Aesthetic quality (composition/lighting)
   - Motion (reject too-static or too-chaotic)
   - OCR (reject overlays, watermarks, hard-coded subtitles)
   - Perceptual quality (blur, compression artefacts)
   - Semantic artefacts (video-in-video, abrupt transitions)
   - VLM-based semantic validation (Qwen2.5-VL)
   - Content-type classifier (reject synthetic, games, animations
     unless target domain)
5. **Dedup** — perceptual + semantic.
6. **Dataset sharding** — WebDataset-style tars for GPU training.
7. **Train/val/test split** by *source video*, not clip, to prevent
   leakage.

## Why we care

- This is the strongest public statement of the "seven filters, in
  order" pattern. Treat it as the **target architecture** for our
  pipeline, not as a wishlist: every component maps to a `specint`
  module we either have, have stubbed, or need to stub.
- Stage 7 (split by source video) is a *correctness* constraint we do
  not currently enforce. Dedup today should be aware of
  `source_native_id` so we never allow the same upstream video to end
  up in both train and eval shards once splits exist.

## Mapping to specint

| Cosmos stage       | specint module (current → target)                                     |
| ------------------ | --------------------------------------------------------------------- |
| Shot splitting     | *missing* → `src/specint/pixel/scenes.py` (future)                   |
| Transcoding        | *out of scope* — we never redistribute pixels                         |
| Captioning         | *missing* → `src/specint/pixel/caption.py` (future, VLM-backed)      |
| Aesthetic / motion / perceptual quality | *missing* → `src/specint/pixel/quality.py` (future)                   |
| OCR / watermark    | *missing* → heuristic metadata filter today (title regex)             |
| Semantic artefacts | *missing* → VLM-based, deferred                                       |
| VLM validation     | *missing* → deferred                                                  |
| Content classifier | *missing* → heuristic via `keywords` and `description` for now        |
| **Dedup**          | **shipping today** → `src/specint/quality/dedup.py`                   |
| Dataset sharding   | *out of scope until we have an actual export flow*                    |
| Train/val/test split | *stub only* — see `src/specint/compare/yield_projection.py` notes   |

## Risks / disagreements

- Cosmos assumes GPU-cheap VLM inference. We will not pay for GPU
  pretraining in CI. Every pixel stage must have a *metadata-only
  fallback* and must be feature-gated.
- NVIDIA ships the Cookbook under its own licence; we treat it as
  reference material, not a source of code or weights to copy. Our
  implementations are clean-room, cited back to this note.
- The Cookbook is prescriptive about aesthetic quality in a way that
  biases toward Western, well-lit cinematography. Our cooking target
  explicitly includes informal, hand-held footage (home kitchens,
  Indian cooking) — the aesthetic filter must therefore be configurable
  per domain and off by default.
