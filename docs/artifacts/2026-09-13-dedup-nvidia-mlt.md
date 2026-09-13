# Dedup at internet scale: NeMo Curator + MLT-Dedup + S5VH

Three complementary references. Together they say: dedup is *not*
"perceptual hash and be done" — it is a **layered** pipeline where each
layer has a specific cost/recall trade-off.

## 1. NVIDIA NeMo Curator (production ready, 2026)

- Docs: https://docs.nvidia.com/nemo/curator/main/curate-video/process-data/dedup

Three stages, each a standalone pipeline node:

- **`KMeansStage`** — partition clip embeddings, record
  `cosine_dist_to_cent`.
- **`PairwiseStage`** — within-cluster cosine similarity on GPU; per
  clip emit `max_id` and `cosine_sim_score`.
- **`IdentifyDuplicatesStage`** — filter pairs with
  `cosine_sim_score >= 1.0 - eps` and write parquet of duplicate ids.

**Key operational insight:** "Determine `eps` first. Run K-means +
pairwise with `eps=None` to *inspect the similarity distribution* before
committing to a threshold." This is the same rule we need for our
metadata-only Jaccard threshold — pick a percentile, not a magic number.

## 2. MLT-Dedup (arXiv:2606.12215, 2026)

- URL: https://arxiv.org/html/2606.12215v1

The state-of-the-art *online* dedup approach:

- **Multi-Level Video Encoder (ML-VE)** — one model emits both
  frame-level and clip-level embeddings. Clip-level does indexing (small
  memory); frame-level lives on disk and is loaded only when a candidate
  survives coarse retrieval.
- **DiF-SiM (Difference-based Spatial-Temporal Matching)** — matches
  frame sequences by their differences, robust to per-frame
  distortions.
- **Dual-modality SSL pretraining** — image + video, because true
  duplicate labels are extremely sparse in the wild.

**Takeaway.** The right architecture is *hierarchical*: cheap-then-
expensive. Our metadata-first pipeline is exactly this pattern applied
one level lower — cheap URL/title dedup before any embedding call.

## 3. S5VH (AAAI 2025)

- URL: https://arxiv.org/abs/2412.14518 (repo:
  https://github.com/gimpong/AAAI25-S5VH)

Bidirectional Mamba video-hashing with a "semantic hash centre" and a
centre-alignment loss. Linear-complexity self-supervised video hashes
that outperform prior CNN/transformer baselines on FIVR / EVVE. When
frame decoding becomes affordable for us, this is the model to use for
the middle tier (between cheap metadata dedup and full ML-VE
embeddings).

## The three-layer dedup contract we should ship

Because we are metadata-only today, only Layer 1 is in scope. But the
data structures should be forward-compatible.

| Layer | Signal                                     | Cost           | Where          |
| ----- | ------------------------------------------ | -------------- | -------------- |
| L1    | canonical URL, media URL, title-shingle    | ns per record  | metadata pass  |
| L2    | video-hash (dHash / videohash) on frames   | ~sec per video | frame pass     |
| L3    | learned clip embedding + ANN clustering    | GPU-hours      | training pass  |

**Concrete for today's Coding-Agent plan:**

1. Add `deduplicate(records, *, url_norm=True, title_jaccard=0.85)` in
   `src/specint/quality/dedup.py`. Pure, deterministic, no I/O.
2. `BenchmarkResult` gains `n_after_dedup: int` and
   `duplicate_pairs: list[tuple[str, str]]` (record-id pairs).
3. Fixture pair: same underlying "Bread rising" video mirrored to
   Wikimedia Commons and Internet Archive with slightly-different titles
   ("Bread rising timelapse" vs "Bread Rising - Timelapse"). Test the
   Jaccard threshold catches it.
4. Placeholder module `src/specint/quality/dedup_l2.py` with a stub
   `NotImplementedError("requires frame decode; see roadmap")` so the
   contract is visible.

## Threshold-choice discipline

Copy NeMo Curator's rule verbatim into `docs/roadmap.md`:

> Never ship a similarity threshold that was not first justified by
> inspecting the empirical similarity distribution on the current
> corpus. `eps` is not a constant.
