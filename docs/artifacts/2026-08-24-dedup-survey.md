# Video Deduplication — Survey & Adoption Plan

## Papers / tools considered

- **MLT-Dedup** (KDD '26, <https://arxiv.org/abs/2606.12215>):
  Multi-Level Video Encoder emits both sparse clip-level embeddings
  (for candidate retrieval) and dense frame-level embeddings (for
  pairwise verification). Reports **91 % reduction in online
  repetition rate at 90 % precision** on a real UGC platform, with
  a 5× candidate-recall gain over single-level baselines.
- **SVD** (ICCV '19, <https://svdbase.github.io/>): 500K short-video
  benchmark for near-duplicate retrieval. Existing SOTA hashing
  methods significantly under-perform on SVD-transformation splits
  (crop, watermark, re-encode) — this is the failure mode we must
  design for.
- **videohash** (<https://github.com/akamhy/videohash>): pure-Python,
  64-bit wavelet hash on a frame-collage. Fine as a smoke-test
  fingerprint; brittle to heavy edits.
- **Backblaze reference impl**
  (<https://github.com/backblaze-b2-samples/videohash-deduplication>):
  demonstrates the naive O(N²) union-find pipeline; explicitly flags
  the need for LSH / BK-tree at 100K+ scale.
- **Perceptual-hash duplicate detection** (Ali et al., 2025, DOI
  `10.1109/ieeeconf67917.2025.11443714`): 64-bit DCT hashes; the
  *uncropped high-frequency* variant beats low-frequency and cropped
  variants on their duplicate benchmark.

## Where dedup belongs in our pipeline

We have three natural chokepoints. Different fingerprints are
appropriate at each.

| Stage                          | Fingerprint                              | Cost per record |
| ------------------------------ | ---------------------------------------- | --------------- |
| **1. URL-level**               | canonical URL + host                     | µs              |
| **2. Metadata-level**          | title 5-shingle Jaccard + author id + `duration_s` bucket | ms |
| **3. Frame-level (post-download)** | videohash → DCT hash → CLIP-ViT embed if collision | seconds |

For today we build stages 1–2 (offline, deterministic, unit-testable).
Stage 3 goes behind an integration marker and is not required until we
actually pull frames.

## Adoption plan (mirrors P1 in the plan)

1. `dedupe/urlhash.py` implements stages 1 & 2. Deterministic. Emits
   an `EquivalenceClass` for every collision.
2. Harness runs stage 2 across all sources for a given query and adds
   a `__deduped__` benchmark row. Per-source rows stay unchanged so
   we retain apples-to-apples comparison over time.
3. Fixture: add two Wikimedia records that are known re-uploads of an
   Internet Archive video (title match, duration within 1 s). Assert
   `__deduped__.n_records == __total__.n_records - 1`.

## Adversarial test cases to add

- Same video, different title casing.
- Same video, same title, `duration_s` off by 2 s (bad muxing).
- Different videos with title Jaccard > 0.85 but different
  `duration_s` (should **not** collapse).
- YouTube `youtu.be/<id>` vs `youtube.com/watch?v=<id>` — must map to
  the same canonical URL.
- Wikimedia `File:Foo.ogv` vs Internet Archive `foo_ogv` — separate
  URLs, same `duration_s` and title stem → must collapse.

## Non-goals for this artifact

- Actual perceptual video hashing (needs frame decode; out of scope
  today).
- Cross-modal dedup (audio-only vs video, or thumbnail vs video) —
  interesting but downstream.
