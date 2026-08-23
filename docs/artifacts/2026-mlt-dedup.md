# MLT-Dedup — multi-level online video deduplication (KDD 2026)

- **Citation:** *MLT-Dedup: Efficient Large-Scale Online Video
  Deduplication via Multi-Level Representations and Spatial-Temporal
  Matching.* KDD 2026 Applied Track.
- **Permalink:** <https://doi.org/10.48550/arxiv.2606.12215>

Also relevant:

- NVIDIA NeMo Curator video-dedup docs
  (K-means + pairwise cosine, `eps` threshold on `cosine_sim_score`).
- `worldcache-cli` (perceptual-hash per-frame cache) and `forge/dedup`
  (episode-level pHash + union-find clustering, tier-0 CPU-only).

## One-paragraph summary

Deduplication frameworks are typically three stages: representation →
candidate retrieval → pairwise matching. MLT-Dedup argues that a single
embedding granularity is either too coarse (misses clip-in-video reuse)
or too memory-heavy (frame-level embeddings blow up the ANN index). It
proposes a *multi-level* embedding — frame + clip + video — indexed
jointly, plus a spatial-temporal matching head that scores candidate
pairs on order-preserving frame alignment. On UGC platforms it hits
higher recall for the same index budget than single-level baselines.

## Transferable to `specint`

- **Cross-source dedup is our #1 unmet quality problem.** Wikimedia,
  Internet Archive, PeerTube mirrors, and Common Crawl recipe pages all
  frequently point at *the same underlying media*. Without dedup, a
  source that mirrors a lot looks artificially high-yield.
- **Cheap, metadata-only tier we can ship today** (no model, no
  network): a `MinHash` over the token shingles of
  `title + description[:500]` + a canonicalised host of `url`.
  Records that collide are candidate duplicates. Emit a new
  `n_intra_source_dup` and `n_cross_source_dup` column on
  `BenchmarkResult`.
- **Tier-1 (needs media): perceptual pHash of thumbnail (a single
  image, always fetchable) → union-find cluster.** Every source we
  target exposes a thumbnail URL cheaply.
- **Tier-2 (needs video): CLIP-embedding + `eps` threshold**, mirroring
  NeMo Curator's workflow. Gated behind `SPECINT_RUN_ANNOTATION=1`.
- **Do not silently delete duplicates.** MLT-Dedup keeps one canonical
  and points others at it. Our schema should add a `duplicate_of:
  str | None` field to preserve provenance chains, per our
  "provenance is mandatory" rule.

## NOT transferable

- MLT-Dedup targets a UGC platform's *serving* pipeline (latency,
  throughput). Our workload is *batch offline curation* — we can afford
  higher-recall / higher-cost algorithms.
- Their proprietary training data isn't relevant; only the algorithm
  and index topology are.

## Adversarial notes

1. Perceptual-hash-only dedup is fragile against re-encodes and
   trimmed clips. For our sources this matters because PeerTube
   mirrors *do* re-encode. Semantic embeddings are needed for a
   defensible cross-source claim.
2. Bogus duplicate reports are worse than missed ones: they inflate
   apparent quality by removing "worse" copies. Any dedup PR must ship
   with a *precision* metric on a labelled fixture set, not just a
   count.
