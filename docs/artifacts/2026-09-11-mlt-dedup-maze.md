# MLT-Dedup + Maze — web-scale video deduplication

- **Citations.**
  - *MLT-Dedup: Efficient Large-Scale Online Video Deduplication via
    Multi-Level Representations and Spatial-Temporal Matching*,
    KDD 2026 (arXiv:2606.12215).
  - *Maze: A Cost-Efficient Video Deduplication System at Web-scale*,
    NSF PAR 10418826 (deployed at ~1.3B videos with ~800k/day inserts).

## One-paragraph summary

MLT-Dedup builds a two-tier index: sparse 768-dim clip-level HNSW
embeddings for candidate retrieval, plus dense 256-dim frame-level
embeddings loaded only for pairwise re-ranking. Their DiF-SiM module
localizes duplicated *segments* (not just whole-video near-dup), which
is critical because most UGC dupes are re-encodes, watermarks, or
partial re-cuts. Reports 91% repetition reduction at 90% precision and
5× index capacity vs a single-level baseline. Maze at ByteDance uses
compact quantized CNN + ORB features with acoustic spectrograms as a
tie-breaker, shards ANNS by insert-time (no cross-node re-training),
and runs the Smith-Waterman algorithm over per-shot feature sequences.

## Why it matters to Specialized-Intelligence

- We have zero dedup today. Wikimedia videos are frequently mirrored on
  Internet Archive and PeerTube; the same Common Crawl recipe page can
  appear across multiple CC snapshots. Our current `__total__` row
  **double-counts these**. This is the single largest measurable
  quality bug in the baseline report.
- The "clip inside video" case is the important one for cooking: a 20
  minute mega-recipe video and a 3 minute "just the sauce" clip are
  near-duplicates from a training perspective and should be
  co-weighted, not treated as independent samples.
- Sharding by ingest time avoids the CI/reproducibility nightmare of a
  global index. We can adopt the same discipline: dedup within a
  crawl-day artifact, across-crawl-day dedup is a separate offline
  merge.

## Concrete ideas to steal

- Immediate: add a URL-canonicalization + `(source, source_native_id)`
  dedup in `compare.harness` today, even though it is only the exact
  match tier. This alone will surface how many current records are
  cross-source repeats.
- Near-term: for records with `media_url`, compute an SHA-256 hash of
  the HTTP `Content-Length + ETag + Last-Modified` triple as a
  "poor-man's fingerprint" without downloading media.
- Medium-term: extract 1 frame per 5s via `ffmpeg` and use a
  perceptual hash (pHash / dHash) to detect re-encodes. Store hashes,
  not frames.
- Long-term: adopt an MLT-Dedup-style two-tier embedding index only
  when the corpus exceeds ~1M records; for the first ~100k
  perceptual hashes + Smith-Waterman on shot sequences (Maze style)
  outperforms a heavier ANN system on both cost and reproducibility.
- Add a `dedup_report.json` alongside every `compare-*.json` that lists
  each collapsed group so the drop is auditable.

## Risks / gotchas

- Perceptual-hash false positives on visually similar but semantically
  different footage (two different pasta recipes shot in the same
  kitchen). Need a text-similarity gate on titles/steps before
  collapsing.
- Do not download media just to hash it — that becomes de-facto
  redistribution. Prefer HEAD-request fingerprints and hash the raw
  bytes we *already* pulled for permitted CC / PD media only.
- Any dedup that collapses across licenses must keep the *most
  permissive* representative (CC0 > CC-BY > CC-BY-SA > OTHER_FREE) so
  the resulting corpus does not silently inherit a stricter license.
