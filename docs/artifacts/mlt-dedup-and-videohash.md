# Near-duplicate video detection — MLT-Dedup and videohash

- **MLT-Dedup:** *Efficient Large-Scale Online Video Deduplication via
  Multi-Level Representations and Spatial-Temporal Matching*
  (arXiv:2606.12215). Multi-level encoder — sparse clip embeddings
  for candidate retrieval + dense frame embeddings for precise
  matching. Reports 91% online-repetition reduction at 90% precision
  on a real large platform.
- **AVHash:** *AVHash: Joint Audio-Visual Hashing for Video Retrieval*
  (OpenReview 2025). Adds audio-visual joint hashing on top of the
  standard perceptual-hash pipeline.
- **videohash (akamhy):** <https://github.com/akamhy/videohash>
  Pure-Python, CPU-only, 64-bit wavelet-hash of a per-second frame
  collage. Robust to re-encodes, resolution changes, watermarks. Good
  enough for our scale.

## Why it matters for Specialized-Intelligence

Weakness **W6** in the 2026-08-25 plan: the same video will show up
across Wikimedia Commons, PeerTube mirrors, and Internet Archive. Our
current aggregate `n_records` triple-counts it, which inflates our
apparent yield and, worse, means the same clip is over-represented in
any training set we hand downstream. We need dedup **before** we
publish training corpora, not after.

MLT-Dedup is overkill for a repo pre-media-download. But its
two-stage design ("cheap candidate retrieval → precise pairwise
match") is the right architecture for when we do start pulling media.

## Concrete implementation ideas

**Phase 1 — metadata only (`W6`, next Coding-Agent PR):**

- `src/specint/dedup/metadata.py`
  - `signature(record) -> tuple[str, int, str]`:
    `(normalize_title(record.title),
      round(record.duration_s or 0),
      normalize_author(record.author))`.
  - `dedupe(records) -> tuple[list[VideoRecord], DedupReport]`.
- `normalize_title`: lowercase, strip punctuation, collapse
  whitespace, drop stopwords, keep as unigram set for Jaccard fallback
  when durations disagree by ±1s.
- Add `n_duplicates_removed` to `BenchmarkResult`.
- Fixture: two `VideoRecord`s with different `source` slugs but
  identical `(title, duration_s, author)` → dedupe collapses them.

**Phase 2 — perceptual (deferred to when media download lands):**

- Wrap `akamhy/videohash` behind a `specint.dedup.perceptual` module.
- Compute hash once per record and persist it in a sidecar column;
  never re-download to re-hash.
- Cluster with Hamming distance ≤ 8 (matches Backblaze reference
  implementation) using union-find.

**Phase 3 — audio-visual (deferred):**

- If Phase 2 recall is insufficient (silent re-encodes, changed
  soundtracks), evaluate AVHash. Ship it only after phase-2 numbers
  are on the board in `reports/`.
