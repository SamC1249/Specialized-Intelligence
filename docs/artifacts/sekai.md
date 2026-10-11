# Sekai — a video dataset for world exploration

- Paper: *Sekai: A Video Dataset towards World Exploration*,
  NeurIPS 2025 Datasets & Benchmarks Track.
- Proceedings PDF:
  <https://proceedings.neurips.cc/paper_files/paper/2025/file/2368d4a3f24122b9f3779aaffa261719-Paper-Datasets_and_Benchmarks_Track.pdf>

## What it is

Sekai builds a world-model training corpus from "walking tour" videos.
Their pipeline (Figure 3) is four stages — collection → pre-processing
→ annotation → sampling — but the pre-processing stage is where the
curation craft lives:

- **Shot boundary detection** — split into coherent clips.
- **Luminance filtering** — drop over/under-exposed clips.
- **Perceptual quality filter** — COVER model, drops low-quality.
- **Subtitle filter** — hard-coded subtitles found with VideoSubFinder
  over the bottom third of the frame; threshold 0.75.
- **Camera trajectory filter** — reject clips with implausible SfM
  trajectories (abrupt reversals, >150° yaw jumps, >5× jitter vs
  neighbouring frames).
- **Content diversity sampling** — InternVideo2 embeddings + mini-batch
  K-Means clustering by country/region, then diverse-sample within
  each cluster.

Final corpus is 6 620 h "Sekai-Real" (plus 60 h Sekai-Game).

## Why we care

- Confirms the industry pattern: *six to eight orthogonal filters, each
  removing a different failure mode, applied in sequence*. A single
  "quality score" cannot stand in for this.
- The **subtitle / hardcoded-text filter** is highly relevant to
  cooking: a lot of CC-BY recipe videos ship with burned-in text
  overlays that are usually fine for humans but poison a world model's
  state-grounding signal.
- The **diversity sampler** is a reminder that "more data" is not the
  goal; *balanced* data is. Our current harness does not sample at all
  — it either keeps or drops.

## Implementation hook

- `src/specint/quality/metrics.py` — reserve a `metadata_only` prefix
  for current scorers; add a parallel `pixel_based` module path for
  future luminance / shot-boundary / subtitle scorers.
- `src/specint/compare/harness.py` — add a `diversity_sample()`
  function that, given a list of scored `VideoRecord`s and a target
  size `N`, returns a subset that maximises author-and-language
  entropy under a budget. Pure, metadata-only, testable today.
- `src/specint/sources/*` — expose per-source `region` tags
  (`country_code` field on `VideoRecord` is a candidate addition; file
  this under schema evolution and update `db_structured.md` in the
  same PR when we add it).

## Risks / disagreements

- Sekai downloads YouTube videos. Same hard-constraint divergence as
  Panda-70M. We lift the *filter catalogue*, not the ingestion path.
- SfM-based trajectory filtering requires frame access. Deferred.
- Their COVER quality model is distributed under its own license; we
  will not bundle it. If/when we add pixel-level scoring, we will
  prefer models with explicit permissive licenses (e.g. the
  Apache-licensed `pyiqa` suite) and record the model's identity in
  `Provenance.extractor`.
