# Annotated bibliography — "what to steal, per paper"

Each entry is one paragraph. Format:

> **[Title]** — venue/year — URL
> **TL;DR:** one or two sentences on what the paper does.
> **What we steal:** concrete, specint-shaped action items.
> **What we don't:** anything incompatible with the hard constraints
> (no paid, no ToS violations, URL+metadata-only).

---

### LAION-BVD: A 10-Million-Hour Open Video Dataset for Multimodal Pre-training (2026)

> arXiv [2608.24845](https://arxiv.org/abs/2608.24845) · code
> [LAION-AI/BVD](https://github.com/LAION-AI/BVD)
>
> **TL;DR.** Mines 1.3B platform-specific video URLs from Common
> Crawl, downloads 80M (10M hours), does PySceneDetect-style scene
> splitting, generates synthetic audio/video captions, trains CLIP-,
> CLAP-, ViCLIP-class models. Explicitly research-only, non-commercial.
>
> **What we steal.**
>
> - The *URL-discovery* half of the pipeline (CC → candidate URLs →
>   dedup) is directly applicable to our Common Crawl URL Index path
>   ([`02-common-crawl-url-index.md`](../02-common-crawl-url-index.md)).
> - Their observation that scene-split clips outperform full videos
>   for most downstream tasks — informs how we design the eventual
>   clip-level dedup / sampling policy without actually downloading
>   bytes yet.
> - Their list of "platform-specific" URL regexes is a treasure map
>   for *excluding* ToS-protected hosts up front.
>
> **What we don't.** The media download step and the resulting
> redistribution — the dataset is non-commercial and we can't ingest
> it even for internal use given AGENTS.md's redistribution rule.

### Panda-70M: Captioning 70M Videos with Multiple Cross-Modality Teachers (CVPR 2024, updated 2024-10)

> site [Panda-70M](https://snap-research.github.io/Panda-70M/) · code
> [snap-research/Panda-70M](https://github.com/snap-research/Panda-70M) · supp
> [PDF](https://openaccess.thecvf.com/content/CVPR2024/supplemental/Chen_Panda-70M_Captioning_70M_CVPR_2024_supplemental.pdf)
>
> **TL;DR.** 70.7M clips (167 kh) harvested from HD-VILA-100M by
> PySceneDetect (threshold 25, min 15 frames) + ImageBind-based
> endpoint-similarity splits (`k f(A)-f(B)k ≤ 1.0`) + 5-second
> recursive splits + semantically-similar-adjacent merge
> (`≤ 0.6`). The Oct-2024 update adds a desirability filter
> (`0_low_desirable_score`, `1_still_foreground_image`,
> `2_tiny_camera_movement`, `3_screen_in_screen`,
> `4_computer_screen_recording`) — only 80.5% of clips are
> "desirable" by their classifier.
>
> **What we steal.**
>
> - The desirability taxonomy is a candidate output of a future
>   frame-sampling QA step. For metadata-only, we encode it as
>   "flags" on `VideoRecord` so a downstream consumer can filter
>   on them without re-watching.
> - The PySceneDetect + endpoint-similarity + 5s-recursive-split
>   recipe is the de-facto standard; adopt it verbatim when we have
>   frames.
> - Their observation that **~20% of raw-crawl video is unusable**
>   is the single strongest argument for metadata triage before any
>   download step. Drives our quality-gate ordering.
>
> **What we don't.** We can't redistribute the dataset itself (it is
> downloaded from third-party sources on demand). The *pipeline* is
> fine to replicate.

### OpenVid-1M filtering heuristics

> As described in the Panda-70M / OpenVid line of work: LAION
> aesthetic score, CLIP temporal consistency, UniMatch optical-flow
> motion, DOVER-Technical clarity, Cascaded Cut Detector scene
> splitting.
>
> **What we steal.** Nothing today (all five are frame-based). But
> this is the hit-list to port into `quality/` once we take a
> position on frame extraction (see
> [`06-fair-use-frames-doctrine.md`](../06-fair-use-frames-doctrine.md)).
> UniMatch optical-flow is particularly interesting because low
> optical-flow = tiny camera movement, which Panda-70M flags as
> undesirable.

### V-JEPA 2 — Self-Supervised Video Models Enable Understanding, Prediction and Planning (2025–2026)

> arXiv [2506.09985](https://arxiv.org/abs/2506.09985) · code
> [facebookresearch/vjepa2](https://github.com/facebookresearch/vjepa2)
>
> **TL;DR.** Trains an action-free Joint-Embedding Predictive
> Architecture on >1M hours of internet video (incl. HowTo100M and
> curated YT1B, totaling 22M samples), then post-trains a tiny
> action-conditioned variant on 62 h of robot interaction data for
> zero-shot pick-and-place. Hits 39.7 R@5 on Epic-Kitchens-100 action
> anticipation.
>
> **What we steal.**
>
> - *Why cooking matters as a benchmark*: Epic-Kitchens-100 is their
>   action-anticipation benchmark; our pipeline's success criterion
>   is "do we produce a training set that moves this needle without
>   paid data?"
> - The design pattern "pretrain action-free on massive, cheap,
>   license-OK video; post-train action-conditioned on tiny
>   trajectory corpora" is the entire business case for this repo.
> - Confirms long-form (minutes-scale) tutorial-style footage is
>   high-value — justifies our bias toward Wikimedia / Internet
>   Archive long takes over PeerTube clips.

### V-JEPA 2.1 — Unlocking Dense Features in Video Self-Supervised Learning (2026)

> arXiv [2603.14482](https://arxiv.org/abs/2603.14482)
>
> **TL;DR.** Adds a Dense Predictive Loss, Deep Self-Supervision,
> and dense features; SOTA on Ego4D short-term object-interaction
> anticipation.
>
> **What we steal.** Reinforces the "dense temporal grounding
> matters" thesis → favour sources with per-frame timestamp /
> caption alignment (JSON-LD `HasPart` with `startOffset`,
> WebVTT caption tracks) when we add caption-presence as a quality
> component.

### P-JEPA — Procedural Video Representation Learning via JEPA (2026)

> arXiv [2606.23256](https://arxiv.org/abs/2606.23256)
>
> **TL;DR.** Applies JEPA-style masked latent prediction to
> *30-minute* procedural videos (EgoExo4D, EgoProceL, Assembly101)
> on top of V-JEPA 2.1 features; learns temporal order and
> procedural progress without narrations or step labels.
>
> **What we steal.** Confirms that long-horizon procedural video is
> the frontier regime. In our scoring, we should prefer `duration_s
> ≥ 30 × 60` cooking videos over short clips when the source
> supports it — once we add `quality_hours` and
> `procedural_density`, the long-form Wikimedia and Archive.org
> items should float to the top of the ranking.

### MLT-Dedup — Efficient Large-Scale Online Video Deduplication (KDD 2026)

> arXiv [2606.12215](https://arxiv.org/html/2606.12215v1)
>
> **TL;DR.** Multi-level video encoder: sparse clip-level embeddings
> for retrieval, dense frame-level embeddings on disk for pairwise
> matching. 91% repetition reduction at 90% precision in a real
> deployment.
>
> **What we steal.** The two-tier architecture (sparse-cheap for
> candidate recall, dense-expensive only for confirmed candidates)
> is the right pattern for an eventual video dedup pass. In the
> metadata-only regime it still motivates a two-tier dedup today:
> URL/host sparse first, then title+description shingling only
> within collisions.

### NVIDIA NeMo Curator — Video Deduplication docs (2026)

> [docs.nvidia.com/nemo/curator](https://docs.nvidia.com/nemo/curator/main/curate-video/process-data/dedup)
>
> **TL;DR.** Open docs: clip-level CLIP embeddings → K-means
> partitioning → within-cluster pairwise cosine similarity on GPU →
> `cosine_sim ≥ 1 - eps` → duplicate IDs out as Parquet. "Tune eps
> from similarity distributions rather than a fixed threshold."
>
> **What we steal.** Operational recipe; particularly the eps-from-
> distribution advice. We should emit a histogram of pairwise
> similarities to `reports/dedup-eps-YYYY-MM-DD.json` and *choose*
> eps per run instead of hardcoding.

### CommonCrawl-CreativeCommons (C5) — multi-signal license parser

> [BramVanroy/CommonCrawl-CreativeCommons](https://github.com/BramVanroy/CommonCrawl-CreativeCommons)
>
> **TL;DR.** Parses full HTML into a tree, extracts license evidence
> from `meta_tag`, `json-ld`, `link_tag`, `a_tag`, records *where*
> the evidence was found (head vs. body vs. footer), and attaches a
> confidence ranking.
>
> **What we steal.** The entire approach — see
> [`03-multisignal-license.md`](../03-multisignal-license.md). This
> is the single clearest external template for the
> `src/specint/licensing/` package.

### WorldCache CLI — perceptual-hash frame dedup

> [dakshjain-1616/worldcache-cli](https://github.com/dakshjain-1616/worldcache-cli)
>
> **TL;DR.** dHash / pHash / aHash / wHash sliding-window cache in
> front of a world model; skips frames with similarity ≥ threshold
> (default 0.92).
>
> **What we steal.** The *interface*: a `--threshold`,
> `--window-size`, `--algorithm` CLI matches the ergonomics we
> should offer when / if we add frame-level dedup. Nothing to ship
> metadata-only.

### KINE-DataPipe — MIT-licensed open video pipeline for world-model pretraining

> [zoahdev/kine-datapipe](https://github.com/zoahdev/kine-datapipe)
>
> **TL;DR.** MIT-licensed single-GPU video pipeline:
> `collect → split → filter --min-motion` for world-model data,
> commercial use welcome.
>
> **What we steal.** The "comparable, single-GPU reproducible"
> philosophy — mirrors our comparison-first rule. Their
> `--min-motion 0.35` default is a sensible seed for optical-flow
> filtering when we eventually add it.
