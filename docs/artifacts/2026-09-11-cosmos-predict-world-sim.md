# Cosmos-Predict2.5 / Reka world-model data pipeline

- **Citation.** *World Simulation with Video Foundation Models for
  Physical AI*, arXiv:2511.00062 (2025-2026). Reka's "World Model Data
  Pipeline" blog post (reka.ai/vision/news/world-model-data-pipeline).
- **Scale.** 200M raw videos in, ~200M curated clips out (~4% pass
  rate), 6B intermediate segments.

## One-paragraph summary

Both papers describe production data engines for training video
foundation / world models. The pipeline is: (1) shot-aware splitting,
(2) GPU transcoding, (3) crop black borders / spatial padding, (4)
multi-stage filtering (aesthetic score, motion analysis, distortion,
OCR/overlay text detection, semantic artifact detection, content
policy), (5) VLM-generated captions, (6) semantic (embedding-based)
deduplication, (7) sharding. Reka additionally emphasises 9+ quality
analysis models scoring each clip and a "cheap analysis first" order to
avoid paying for full analysis of trivially bad clips.

## Why it matters to Specialized-Intelligence

- Our current quality scorer is *metadata-only* and heuristic. That's
  fine for a triage-before-download decision, but the papers make clear
  that the true quality signal only appears after (cheap) frame-level
  analysis. We need a two-tier scorer: metadata triage → cheap
  frame-level analysis on the survivors.
- The "chicken and egg" problem (need to look at video to filter it,
  but want to filter before looking) maps directly to our
  license-first-then-quality problem. Same solution: coarse-to-fine
  gates in a defined order, each cheap enough that the false-negative
  cost is bounded.
- 4% pass-through rate is the *upper bound* on retention we should
  design for. Our benchmark harness should log `n_dropped_by_stage` so
  we can measure this.

## Concrete ideas to steal

- Add a `stages` field to `BenchmarkResult` that records how many
  records were dropped at each gate (license, duration, resolution,
  text_density, dedup). Today we only get the final `n_records`.
- Introduce a `dedup` stage to `compare.harness` that runs before the
  aggregate `__total__` row so that near-duplicates across sources
  (e.g. same Wikimedia video mirrored on Internet Archive) don't
  double-count.
- Add a `frame_probe` optional stage: for `license_clean` records only,
  pull a single keyframe via `ffmpeg -ss` and cheaply test
  (a) not-corrupt, (b) not-all-black, (c) has motion. This keeps us
  metadata-only for the majority of records but lets us upgrade quality
  scores on the survivors.
- Adopt an "aesthetic score" that is *not* an aesthetic score — for
  world-model training we care about motion diversity and object
  density, not beauty. Track separately from `mean_quality`.

## Risks / gotchas

- Reka pipeline is closed source and Cosmos uses proprietary datasets;
  we can steal architecture, not weights.
- Do not paste in filter thresholds (aesthetic > X, motion > Y)
  without re-tuning against our specific corpus — the distributions
  differ.
- Deduplication that is too aggressive collapses training signal for
  rare recipes; the papers accept 10-15% recall loss for 90% precision
  as the operating point. We should log ROC, not a single threshold.
