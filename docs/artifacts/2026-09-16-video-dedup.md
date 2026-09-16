# Video near-duplicate detection — SSCD, pHash, VSC2022

- **VSC2022** — Meta's Video Similarity Challenge, 2022.
  [baseline docs](https://github.com/facebookresearch/vsc2022/blob/main/docs/baseline.md).
- **SSCD** — Pizzi et al. "A Self-Supervised Descriptor for Image Copy
  Detection", CVPR 2022. [arXiv:2202.10261](https://arxiv.org/abs/2202.10261).
- **Perceptual hashing (pHash)** — long-standing folklore; a good 2024
  reference implementation for videos is
  [VidDup](https://github.com/Pengfei-Kou/viddup) (xxHash → duration
  bucket → 10-frame pHash with median-Hamming).
- **PHVSpec** — Technology Coalition benchmark, 2024. [PDF](https://technologycoalition.org/wp-content/uploads/Tech-Coalition-Video-Hash-Benchmark-Paper.pdf).
- **Extremely compact video representation for efficient
  near-duplicates detection** — Pattern Recognition 2024.
  [DOI](https://doi.org/10.1016/j.patcog.2024.111016).

## Why we care

At internet scale, mirrors and re-uploads dominate. On our current
allowlist alone we already have cross-source duplication risk (Common
Crawl recipe pages routinely embed the same Vimeo/YouTube video that
also appears elsewhere; Archive.org uploads mirror Commons; PeerTube
instances re-federate each other). Without dedup, our
"total_duration_s" is inflated and our "unique_authors" is
optimistic.

## Three-tier design (adapt from VidDup)

Tier | Cost | Catches
--- | --- | ---
L1: canonical URL + file hash | O(1) per record | exact re-uploads, mirror URLs
L2: metadata bucket (duration ±5%, resolution class) | O(1) per record | near-copies with mild transcode
L3: perceptual (pHash 10-frame median, or SSCD embedding) | O(N·f) | re-encodes, scaled/cropped copies

At **metadata-only** stage (where we live today), we can already run
L1 and L2. L3 waits for a download stage. Even L1 + L2 removes the
easy wins.

### L1 — canonical URL
- Strip common tracking params (`?utm_*`, `?feature=youtu.be`).
- Resolve known aliases: `youtu.be/{id}` → `youtube.com/watch?v={id}`,
  `commons.wikimedia.org/wiki/File:X` ↔
  `commons.wikimedia.org/wiki/Special:FilePath/X`, PeerTube instance
  aliases via the `federatedInstance` field.

### L2 — metadata bucket
- Key: `(duration_bucket, resolution_class, author_hash, title_shingle)`
  where `duration_bucket = round(duration_s / 5)`,
  `resolution_class ∈ {"<480", "480-719", "720-1079", ">=1080"}`, and
  `title_shingle = min-hash over 5-grams of normalized title`.
- Any two records sharing this key are candidates.

## What we can steal (from SSCD & VSC2022)

- **Score-normalization** is essential to trade off precision/recall
  across sources. We should emit *raw* similarity scores in reports,
  not thresholded 0/1 dedup decisions, so the harness can pick the
  operating point per experiment.
- **Temporal alignment via VCSL's TN algorithm** for L3 is overkill
  right now, but the localisation-first framing (which clip range of
  A matches which clip range of B) will matter once we start slicing
  long videos into 3 s pretraining clips à la V-JEPA.

## What we must *not* copy

- PHVSpec is CSAM-focused: use it as a *quality benchmark for hash
  algorithms*, not as a data source or model target.
- VSC2022 training data is Facebook AI Research license; the descriptor
  is Apache 2.0. We can *use* SSCD; we must not redistribute the
  descriptor training data.

## Implementation hooks (safe to ship at metadata-only stage)

- `src/specint/quality/dedup.py` → new module implementing L1 (URL
  canonicalization) and L2 (metadata bucket) as pure functions.
- `src/specint/compare/harness.py` → new `BenchmarkResult` field
  `n_after_dedup: int`, plus a top-level `duplicate_rate` on the
  `__total__` row.
- `tests/test_dedup.py` → offline fixtures pairing a Wikimedia and an
  Archive.org record that are actually the same NASA moon-landing
  reel; assert L1 + L2 collapse them to one.
