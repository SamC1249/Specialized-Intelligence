# Artifact — Video deduplication at scale (tiered perceptual → semantic)

**Access date:** 2026-11-11.

## Sources surveyed

| Project | URL | What it provides |
| --- | --- | --- |
| Backblaze `videohash-deduplication` | https://github.com/backblaze-b2-samples/videohash-deduplication | End-to-end demo: frame-sample → wavelet pHash → Hamming-distance + union-find clustering. Honest "move to LSH/BK-tree at 100k+ scale" note. |
| Forge `forge/dedup` | https://github.com/arpitg1304/forge/blob/main/forge/dedup/README.md | Per-episode perceptual signature (K uniformly-sampled keyframes, pHash/dHash/aHash), union-find clustering, "keep representative" policy. Tier-0 is numpy-only. |
| NeMo Curator — Deduplication Concepts | https://docs.nvidia.com/nemo/curator/about/concepts/deduplication | Three-tier taxonomy: exact (MD5), fuzzy (MinHash + LSH), semantic (embeddings + K-means). Video dedup sits in the semantic tier. |
| NVIDIA Cosmos Curator — video pipelines | https://github.com/NVIDIA/cosmos-curator/blob/main/docs/curator/reference/video-pipelines.md | Production-style pipeline: split-annotate → embeddings → K-means-centroid semantic dedup. |
| VID blog, *Video Hashing for Deduplication at Scale* | https://vid.co/blog/video-hashing-for-deduplication-at-scale | Operational guidance: consistent preprocessing, versioned hashers, calibrated thresholds, LSH/PQ/graph indexes. |

## Tiered dedup architecture (consensus)

```
Tier 0  Exact                    SHA-256 of bytes                     ~free
Tier 1  Metadata near-dup        title-shingle MinHash + duration ±X%  cheap, pre-download
Tier 2  Keyframe perceptual      pHash of K sampled frames, pairwise Hamming + union-find
Tier 3  Semantic                 video embeddings → K-means → within-cluster cosine
```

Tiers 2 and 3 require downloaded bytes, so they are out of scope
today. Tier 1 is **pre-download** and is exactly what we can and
should ship now.

## What this means for Specialized-Intelligence today

Our `BenchmarkResult.n_records` currently counts duplicates as
independent — Wikimedia and Internet Archive frequently host the
same CC-BY cooking clip, and Common Crawl recipe pages often embed
PeerTube or Vimeo mirrors of the same source. Without Tier 1 dedup,
we systematically overstate our yield and *understate* mean quality
(because the best-quality representative is diluted by its lower-
quality mirrors).

## Implementable takeaways for `Coding-Agent`

- `src/specint/quality/dedup.py`:
  - `normalize_title(s: str) -> str`: lowercase, NFKD, strip
    punctuation, collapse whitespace.
  - `title_shingles(s: str, k: int = 5) -> set[str]`.
  - `title_minhash(s: str, num_perm: int = 64) -> np.ndarray`.
  - `duration_bucket(d: float | None, tol: float = 0.02) -> int |
    None`.
  - `cluster_near_duplicates(records, title_jaccard_min: float =
    0.7, require_duration_match: bool = True) ->
    list[list[VideoRecord]]`.
- Harness integration:
  - Run dedup *after* quality scoring; sort each cluster by
    `quality_score desc` and keep the first.
  - Report `n_records_raw`, `n_records_unique`, `dedup_rate` (new
    columns in `BenchmarkResult` and `db_structured.md`).
- Tests:
  - Hand-build a cluster of 4 records (same title, same duration ±
    1s, across 4 sources). Assert cluster size 4, kept record from
    the source with highest quality score, tie-break deterministic
    on `source` slug.
- Explicitly document in `dedup.py` that this is a **Tier-1 upper
  bound** — true near-duplicate detection needs Tier 2/3 which
  requires download. We will not claim "deduplicated" without the
  tier qualifier.

## Threshold calibration (future)

Once Tier 2 is possible, the VID blog's advice is correct and
specific: calibrate Hamming thresholds on a labeled set that
*reflects your content*. For cooking, a "same recipe, different
chef" pair is a near-duplicate at the *task* level but a
*different sample* at the visual level — those must not be
collapsed. This argues for keeping Tier 1 (title+duration) as the
only automatic layer and leaving Tier 2/3 behind a human-reviewed
threshold.
