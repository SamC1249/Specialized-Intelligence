# NVIDIA Cosmos Cookbook + NeMo Curator — the reference video curation pipeline

- Docs: https://nvidia-cosmos.github.io/cosmos-cookbook/core_concepts/data_curation/overview.html
- Repo: https://github.com/NVIDIA-NeMo/Curator (26.04 release, April 2026)
- Accessed: 2026-08-20.

## What it does

Cosmos Curator is the pipeline behind NVIDIA's Cosmos world-model
training corpus. It is engineered around **Ray-distributed pipelines**
that transform heterogeneous raw video into structured, sharded,
dedup'd training data across five canonical stages:

1. **Video splitting** — long videos cut into ~5s clips at shot
   boundaries.
2. **Transcoding** — normalize codec/container/fps for downstream
   readers.
3. **Filtering** — bank of ≥9 QA models score aesthetics, motion,
   text-in-frame, blur, NSFW, etc. Clips are binned into quality
   tiers.
4. **Captioning** — VLM captions per clip with short/medium/long
   variants and motion descriptors.
5. **Semantic deduplication** — embed clips, cluster (k-means), and
   keep one representative per cluster (highest resolution wins).

Post-training scale: 100s of millions of clips. NeMo Curator abstracts
the same pipeline over text, image, video, and audio modalities.

## Why it matters for us

We are much smaller and, more importantly, **legally constrained**:
Cosmos-Curator assumes you already own the source video. Our
bottleneck is *sourcing*, not scaling GPU pipelines. But the pipeline
**topology** is exactly the right shape for the moment we get to
frame extraction: sourcing → normalize → QA-bank → caption → dedup.

## Ideas we should steal

1. **Multi-signal QA bank** rather than a single scalar quality score.
   Landing site: `quality/metrics.py` should evolve from a single
   `score_record` to a *vector* of per-component scores, with the
   weighted sum kept for backwards-compatibility. Downstream training
   can then re-weight offline. **Today**: keep `WEIGHTS` explicit so we
   can already report per-component contributions.
2. **"Structured sharding" along (content type, resolution, aspect
   ratio, duration)**. Landing site: the `BenchmarkResult` schema —
   add per-bucket aggregates so we can see *within a source* where the
   yield is coming from. Do this only when we have >1e4 records.
3. **Semantic deduplication** with clip embeddings. We cannot afford
   GPU embeddings today, but we can implement a metadata-only
   near-duplicate detector (title+description shingling +
   MinHash-style hashing) as a cheap first pass. Landing site:
   `src/specint/dedup/`.
4. **Online (incremental) dedup** rather than batch. Our crawl-day
   model naturally wants online dedup: new candidates are checked
   against the cluster centroids of already-accepted records.

## Ideas we should refuse

- Running the whole Ray-distributed pipeline as a hard dependency.
  Our CI is offline and single-process; we should re-implement the
  *interfaces* (`Splitter`, `Filter`, `Captioner`, `Deduper`) rather
  than take a dependency on Ray or NeMo Curator itself.
- Trusting NSFW/aesthetics classifiers uncritically. These models
  encode strong Western-media biases and will systematically
  under-yield underrepresented cuisines. Any aesthetics filter we add
  must ship with a per-language / per-cuisine ablation in `compare/`.

## Follow-ups for `plan-YYYY-MM-DD.md`

- Draft the `src/specint/dedup/minhash.py` metadata-only deduper.
- Extend `BenchmarkResult` with a `by_bucket` field (dict[str, sub-agg])
  so the harness reports per-(resolution × language) breakdowns.
