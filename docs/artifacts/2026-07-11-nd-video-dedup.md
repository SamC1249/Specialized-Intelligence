# Cross-source near-duplicate video detection

_Adversarial-Agent, 2026-07-11_

## The adversary

Two independent sources returning "the same" video (e.g. a Wikimedia
video mirrored to Internet Archive, or a Common Crawl page embedding a
PeerTube URL) will double-count in `BenchmarkResult.n_records` and
`total_duration_s`. Every subsequent decision — how much to spend on a
crawl, which source dominates the yield curve — is silently biased by
this. **Deduplication is a first-class quality signal, not an
optimization.**

## What the literature does

- **Perceptual video hashing** (`videohash`, `videohash2`) generates a
  64-bit code from a 1 fps frame collage; XOR/Hamming distance ranks
  near-duplicates. Works on transcodes, rescales, watermarks. Cheap and
  storage-friendly but requires media download.
  Sources: <https://github.com/akamhy/videohash>,
  <https://pypi.org/project/videohash2/>
- **Frame-level to clip-level self-supervised retrieval** (3D-CSL,
  SIGIR-2022 VRL). Pretrain a 3D encoder with SimCLR-style contrastive
  loss on Kinetics-400, aggregate frame features into a clip-level
  Transformer, binarize with IsoHash for Hamming search. Storage drops
  ~78% versus frame-level features. Overkill for us until we have
  media — cite for future work.
  Sources: <https://arxiv.org/abs/2211.05352>,
  <https://hexiangteng.github.io/papers/SIGIR%202022.pdf>
- **Benchmarks**: FIVR-200K, SVD, CC_WEB_VIDEO for evaluating NDVR
  quality end-to-end.

## What we can do *today* (metadata-only)

We already store enough to detect the vast majority of cross-source
duplicates without downloading a single frame:

1. `media_url` domain + basename equality (a Commons file
   `File:Boiling_eggs.webm` mirrored to Archive as `boiling_eggs.mp4`).
2. `duration_s` bucketed to nearest 2 seconds — a "same-video" signal
   because independent transcodes preserve duration to within 1 s.
3. Normalized title trigram set (lowercase, strip non-alnum,
   `set(zip(*[chars[i:] for i in range(3)]))`), Jaccard >= 0.8.
4. `author` string equality (after unicode NFKC and lowercase).

**Composite key**: two records with the same `duration_bucket` and
title-Jaccard >= 0.8 **or** same author, are considered dupes and the
higher-quality one wins.

This is deliberately *conservative*: false positives here silently
discard training data, so we prefer to keep both and flag them in a
`duplicate_group_id` column when in doubt.

## Downstream benchmark deltas we should now emit

Add to `BenchmarkResult`:

- `n_unique_across_sources`: after cross-source dedup, how many
  records survive.
- `duplicate_rate`: `1 - n_unique_across_sources / n_records`.
- `unique_duration_s`: sum of dedup-winner durations.

If Wikimedia and Archive.org each report 500 hours of cooking video but
the cross-source `duplicate_rate` is 0.6, the *actual* new yield of
adding Archive.org on top of Commons is ~200 hours, not 500. Without
this measurement we would keep believing Archive.org has better yield
than it does.

## Roadmap for media-level dedup (when we start downloading)

1. When media download is enabled, compute `videohash2` on a
   thumbnail-quality re-encode (~144x144, 1 fps). Store as an integer.
2. Union-Find across records whose 64-bit hashes fall within Hamming
   distance 4 (empirically robust for `videohash`).
3. Emit `n_unique_media_hashes` in benchmark reports.
4. Verify metadata-only dedup by comparing group-assignments against
   media-hash groups on the same fixture; publish a precision/recall
   number.
