# papers.md — Annotated bibliography

Research artifacts that directly shape **Specialized-Intelligence**'s
data-collection design. Each entry answers three questions:

1. **What did they build?** (one paragraph)
2. **What is the measurable claim we can borrow?** (concrete numbers)
3. **What should we actually implement from this paper?** (ties to the
   `Coding-Agent` deliverables list in `docs/plan-2026-10-13.md`)

Papers are grouped by the sub-problem they inform. Where a paper is
"inspirational but not directly runnable" we note that explicitly to
avoid cargo-culting.

---

## A. Legal-at-scale video corpora

### A1. SolarWM — "Open Data and Scalable Training for Long-Horizon Video World Models" (arXiv:2609.02886, 2026)

- **What.** A unified pipeline that converts 1.43M clips across **10
  heterogeneous open datasets** into a single frame-aligned contract
  (visual observations, metric camera geometry, captions, quality
  metadata, selection decisions, provenance). Releases data + weights +
  recipes.
- **Measurable claim.** Four 5B–33B models trained on 5-second clips
  achieve real-time causal rollout from minutes to hours; the recipe is
  three stages (bidirectional adaptation, teacher-forced autoregressive
  init, distribution-matching distillation).
- **For us.** The *contract* is the lesson, not the model. Our
  `VideoRecord` schema is the equivalent — we should extend it to carry
  (a) `selection_decisions: list[str]` (why the sampler kept this clip)
  and (b) `camera_geometry: dict | None` once we start downloading
  frames. SolarWM also demonstrates that *per-source* adapters that emit
  a shared canonical format can be mixed by a downstream data engine
  without model-side rewrites — the architecture we already have.

### A2. Sekai / Sekai2 — "A Video Dataset towards World Exploration" (arXiv:2506.15675, 2025 / arXiv:2608.09449, 2026)

- **What.** 5000+ hours of egocentric YouTube footage (Sekai) plus
  128,892 clips / 2,826 hours with per-frame camera trajectories and
  temporally grounded captions (Sekai2). Panoramic revisit sequences
  explicitly target long-term spatial memory.
- **Measurable claim.** 43,594 of 120-second segments reach the full
  two minutes (51.4% of all footage) — i.e., long sustained
  observations dominate the mass of the dataset.
- **For us.** Two takeaways. First, "YouTube" is used *responsibly*
  here as a *URL + annotation* source, not a bulk-download target —
  which matches our `AGENTS.md` constraint. Second, their 120-second
  decomposition is a defensible clip length for world models; we should
  add a `clip_window_s` field to `BenchmarkResult` so sources can be
  compared on *useful* duration, not just raw duration. **Caveat.**
  Sekai hugging-face mirror does not re-upload YouTube media, which is
  the only reason the release is defensible — we must do the same.

### A3. V3C2 — "Vimeo Creative Commons Collection" (NIST, 2023)

- **What.** 9,760 CC-licensed Vimeo videos (1.6 TB, 1,300 h), segmented
  into 1,425,454 shots with keyframes + thumbnails. Explicit data
  agreement, no scraping.
- **Measurable claim.** Mean duration 8 min; all metadata (title,
  keywords, description) in JSON.
- **For us.** This is the *canonical* legal Vimeo-at-scale dataset. It
  is *already-licensed derivative work* — we can rehost keyframes under
  the NIST data agreement. For the cooking subset we should (i) filter
  V3C2 keywords for cooking terms (multilingual) and (ii) use the
  existing shot boundaries as our clip windows. Deliver as
  `src/specint/sources/v3c2_local.py` once we have the dataset on disk;
  no new network dependency.

### A4. Europeana cultural-heritage video API

- **What.** EU public cultural-heritage aggregator. Search API
  `https://api.europeana.eu/record/v2/search.json?type=VIDEO&reusability=open`
  returns CC-BY / CC-BY-SA / PDM / CC0 records with full metadata.
  "ContentTier 4" filter restricts to vertical ≥ 480p **and** a fully
  open rights statement.
- **For us.** Direct candidate adapter (`sources-shortlist.md` entry
  §B2). Cooking is a niche here, but surgery/history/craft is dense —
  this is the first adapter that *proves* the system generalises beyond
  cooking.

### A5. Openverse (WordPress Foundation)

- **What.** Successor to CC Search. Indexes 800M+ CC/PD images and
  audio across providers; serves *video* as "external source" URL
  builders only (Vimeo CC, Europeana VIDEO, Wikimedia Commons video,
  Flickr videos CC).
- **For us.** We cannot query Openverse for video directly, but their
  URL builders are a vetted multi-provider CC-query pattern. We will
  port those patterns into `openverse_proxy.py` to produce *landing-URL
  records only* — valuable primarily as a **deduplication oracle** that
  catches the same clip under three different adapters.

---

## B. Procedural / "difficult" video benchmarks

These are *evaluation* datasets we cannot redistribute, but their
annotation schemas tell us what metadata we must capture if we want our
own corpus to be useful for the same downstream tasks.

### B1. YouCook2 — Zhou et al., AAAI 2018

- **What.** 2,000 third-person cooking videos (176 h, mean 5.26 min
  each) across 89 recipes, with temporally localised imperative-English
  step annotations.
- **For us.** The 5-minute mean duration and the per-step imperative
  text are a published yardstick for "a useful cooking video." Our
  quality scorer's duration component already peaks at 300 s — matches
  YouCook2's mean. We should add a `n_steps` property to `VideoRecord`
  (Common Crawl Recipe schema already gives us this) and compute
  `mean_steps_per_record` as a new `BenchmarkResult` column.

### B2. EPIC-KITCHENS — Damen et al., ECCV 2018 (and VISOR 2022)

- **What.** 55 h of unscripted first-person kitchen video from 32
  participants; 39.6K action segments, 454K bounding boxes. Participants
  narrated their own videos post-hoc.
- **For us.** First-person is the *hard* case for world models — hands
  occlude, state transitions are irreversible, intent is dense. Our
  current four sources are overwhelmingly third-person. We need a
  dedicated search strategy for first-person CC video (GoPro / egocentric
  tag on Commons, "pov cooking" on PeerTube, egocentric categories on
  Vimeo CC). Add `is_egocentric: bool | None` to `VideoRecord`.

### B3. Ego4D Goal-Step — NeurIPS 2023 D&B

- **What.** 7,353 videos / 2,807 h with goal annotations across 319
  goals / 34 scenarios; cooking subset has 47,721 densely labelled
  step/substep segments (430 h, taxonomy of 86 goals × 514 substeps).
- **For us.** Taxonomy depth is the signal to chase. A single cooking
  video can be labelled with up to 514 substeps — i.e., *procedural
  density* is the right axis to differentiate "high-quality training
  example" from "random cooking B-roll." We should add `procedural_density`
  to the quality scorer and derive it from `len(recipe_steps) /
  duration_s` whenever both are known.

### B4. Ego2World — arXiv:2605.13335, 2026

- **What.** Compiles HD-EPIC egocentric cooking annotations into
  executable symbolic worlds (object instances, functional areas,
  symbolic states, 155 executable action types, 426 goal-task
  instances). First benchmark with hidden-state + partial-observation
  + replanning signals grounded in real video.
- **For us.** This paper names the *downstream* evaluation we want our
  data to feed. Even if we never implement an Ego2World-style
  compiler, we should make sure the metadata we capture is sufficient
  to drive one: specifically the (video → recipe-step → object-list)
  triples we are already extracting from `schema.org/Recipe`. Add a
  `n_entities` field (count of unique nouns in `recipe_steps`) as a
  weak proxy for state-space richness.

---

## C. Dataset deduplication

### C1. FED — "Fast and Efficient Dataset Deduplication Framework with GPU Acceleration" (arXiv:2501.01046, 2025)

- **What.** GPU-accelerated MinHash LSH that reaches **≥0.95 Jaccard
  agreement** with the standard CPU MinHash while running up to 260×
  faster. Deduped 1.2T tokens in 6 hours on 16 GPUs.
- **For us.** Overkill at today's scale (<10 fixtures). Keep as a
  future north star for when we hit >100M records. For v0 of our dedup
  cascade (`docs/artifacts/dedup-strategy.md` stage 2), stock
  `datasketch.MinHashLSH` on CPU is fine.

### C2. "Fast distributed video deduplication via LSH with similarity ranking" (Springer JIVP, 2019)

- **What.** Generic hash-based framework: per-keyframe binary hash →
  LSH buckets → candidate videos → re-rank by key-frame similarity on
  MapReduce.
- **For us.** The *framework* (not the Spark/MapReduce layer) is the
  blueprint for `dedup-strategy.md` stage 3. Note we do not download
  frames yet — stage 3 is deferred until we build the frame-fair-use
  pipeline.

### C3. ViDupe — "Duplicate Video Detection as a Service" (IFIP IM 2019)

- **What.** Multi-signal: file hash → cluster by duration (±1 s) →
  DCT keyframe pHash → audio fingerprint. Deployed as a Google Drive
  dedup service.
- **For us.** The ordering of filters — cheapest first (duration),
  then pHash, then audio — is the right cascade shape. Our metadata-only
  stage 1 can already cluster by `duration_s` and `media_url` basename
  without touching any media.

---

## D. Common Crawl at scale (infra reference)

### D1. Common Crawl URL Index (formerly Columnar Index)

- **What.** Apache Parquet index at `s3://commoncrawl/cc-index/table/cc-main/warc/`,
  partitioned by `crawl` and `subset`. Starting with `CC-MAIN-2026-30`
  the Parquet is ZStandard-compressed and includes a `warc_record_id`
  UUID column.
- **How to use.** Query with DuckDB / Athena / Polars for candidate
  URLs, retrieve WARC records via `warc_filename` + `warc_record_offset`
  + `warc_record_length` HTTP range requests, then parse the embedded
  HTML for `schema.org/Recipe.video` or `schema.org/VideoObject`.
- **For us.** This is deliverable 7 in the plan. Our current
  `common_crawl.py` adapter only parses a hand-provided HTML blob — the
  real adapter *starts* at the URL index.

### D2. Google Recipe schema markup

- **What.** Official spec for `schema.org/Recipe`. `video` is a
  `VideoObject`; `step.video` can be `VideoObject` or `Clip`. Required
  fields include `name`, `image`, `recipeIngredient`, `recipeInstructions`.
- **For us.** `recipe_steps` on `VideoRecord` is directly populated
  from `recipeInstructions[*].text`. Add an extraction for
  `step.video.contentUrl` + `step.video.duration` so we can harvest
  *per-step* micro-clips, which are gold for procedural supervision.

---

## E. Reading-list follow-ups (not yet digested)

- MiraData, DL3DV, ABOT-World, OmniWorld — SolarWM's other 7 source
  datasets. Each needs its own §A entry; summarise in the next
  Adversarial-Agent plan.
- HowTo100M (Miech et al., 2019) — the historical YouTube cooking
  dataset; useful as a *negative example* of the all-rights-reserved
  pitfall `AGENTS.md` forbids.
- COIN (Tang et al., 2019) — 11,827 videos / 180 tasks instructional,
  12 domains. Lays out a *task taxonomy* we can reuse for seed-term
  expansion.
- "Something-Something V2" — not procedural but tests fine-grained
  action understanding; useful as a quality-filter sanity check once
  we have frame-level data.
