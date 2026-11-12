# Cosmos World Foundation Model Platform (+ Cosmos-Curator)

- **Paper:** "Cosmos World Foundation Model Platform for Physical AI",
  NVIDIA, arXiv 2501.03575 (v3, 2025/2026).
  <https://arxiv.org/html/2501.03575v3>
- **Code:** <https://github.com/nvidia-cosmos/cosmos-curate>
  (Apache-2.0; permissive).
- **Scale:** ~20 M hours of raw video, 720p–4k, curated down to the
  training set for the Cosmos world foundation models.

## One-line summary

A permissively-licensed, GPU-streaming 5-stage video curation pipeline —
split → filter → annotate → dedupe → shard — explicitly designed for
world-model training data, with each stage open-sourced and documented.

## Why it matters to us (cross-ref to plan-2026-11-12)

- **H5 (dedup):** Cosmos uses K-means on visual embeddings with cosine
  similarity, then "drop within each cluster". VidaForge does the same
  with PDQ + Cosmos-Embed. Both say dedup is a *first-class stage*, not
  an afterthought. Our pipeline has zero dedup today.
- **H4 (procedural density) and the mean_quality attack (D3):** Cosmos's
  filtering stage composes DOVER (perceptual quality) + LAION aesthetic
  + motion score + text-overlay detection. None of that is metadata-only;
  all of it operates on frames. Our *metadata-only* scorer is cheap but
  cannot discriminate within a single source. We should keep metadata
  scoring as the triage layer and plan an optional frame-level enrichment
  stage behind a `--enrich-frames` flag.
- **Generalisation (H6, QualityProfile):** Cosmos ships separate filter
  configs for "pre-training" vs "fine-tuning" vs "video-type-balanced".
  That is exactly the `QualityProfile` abstraction we need.

## What we can / can't copy

- **Can:** The pipeline architecture, the 5-stage naming, the Apache-2.0
  code itself (we can depend on `cosmos-xenna` or just vendor the
  interfaces).
- **Can't / must not:** Their training data itself is not released as
  bulk media. Our constraint (CC-BY/CC0/PD only) is *stricter* than
  Cosmos's — Cosmos's curator is agnostic to source legality. We must
  not import any of their crawled corpora.

## Concrete actions

1. Mirror the 5-stage vocabulary in `src/specint/` (we have `sources` =
   "ingest", `quality` = "filter"; add `dedupe/` and `shard/` as empty
   package skeletons so later PRs have a home).
2. Add `effective_yield_hours` as the headline metric because Cosmos
   reports "hours retained after each filtering stage" as their primary
   yield number, not a mean score.
3. Note: Cosmos's "visual quality" model (DOVER) is permissively
   licensed and can be a downstream dependency for the *enrichment*
   stage, outside CI's offline constraint.
