# V-JEPA 2 / 2.1 — cluster-based retrieval curation on YT-1B

## Citation

- Assran et al. *V-JEPA 2: Self-Supervised Video Models Enable
  Understanding, Prediction and Planning.* arXiv:2506.09985, 2025.
- V-JEPA 2.1: *Unlocking Dense Features in Video Self-Supervised
  Learning.* arXiv:2603.14482, 2026 (preprint).
- Reference: <https://github.com/facebookresearch/vjepa2>

## One-paragraph summary

V-JEPA 2 pretrains a 1B-param joint-embedding predictive video model on
**VideoMix22M**, itself a source-weighted blend of Something-Something
v2, Kinetics 400/600/700, HowTo100M, and a **retrieval-curated** slice
of YT-Temporal-1B (1.4M raw video-hours → 19M curated samples). The
"retrieval curation" step is the interesting one for us: they extract
scenes from raw YT-1B, embed each scene, then run a cluster-based
retrieval procedure that biases the sampled distribution toward the
target evaluation distributions (Kinetics, SSv2, COIN, EPIC-KITCHENS).
The paper reports **+1.4 downstream points** attributable to this
curation. V-JEPA 2.1 doubles down: it shifts source weight further
toward YT-1B and adds dense-prediction / deep-self-supervision losses
to squeeze more supervision signal per token.

## What it changes for `specint`

- Our `quality/metrics.py` today ranks candidates by metadata-only
  proxies (license, duration, resolution, text density, has_steps).
  The V-JEPA 2 result is a strong signal that **content-embedding-based
  curation is the actual frontier lever**. Roadmap: add a
  `quality/embedding_curation.py` module that, given per-record thumbnail
  or first-frame embeddings, samples toward a target-distribution
  centroid. (Blocked on: we need thumbnails, which requires a media-fetch
  worker; see the "no perceptual hash yet" non-goal in
  `docs/plan-2026-07-12.md`.)
- Their source-weighted sampling matches our `BenchmarkResult` per-source
  breakdown. We should ship a `--target-distribution` flag on
  `python -m specint compare` that computes the KL-divergence between
  our observed per-source distribution and a user-supplied target
  (defaults: uniform, EPIC-KITCHENS-like, HowTo100M-like).
- Their reported baseline that "uncurated YT-1B *hurts* downstream" is
  strong prior evidence for **H2 (dedup)** in the 2026-07-12 plan:
  duplicated / near-duplicated procedural footage is not a free lunch.
- Their target-distribution list (Kinetics, SSv2, COIN, EK) contains no
  procedural cooking dataset with a permissive license. This is our
  wedge: if `specint` can produce a *CC-clean*, cooking-heavy,
  curation-ready corpus, we serve a niche the V-JEPA-style pipelines
  can't legally consume.

## Attack surface

- The "retrieval curation gives +1.4" number is measured against fixed
  evaluation sets that themselves are biased toward Meta's downstream
  benchmarks. Under a different downstream (e.g., ours: long-horizon
  procedural reasoning), the sign of the curation effect could shrink or
  even flip. Do not treat the +1.4 as a universal law.
- Their pipeline embeds scenes with a DINOv2-family image encoder.
  Cooking-specific fine motor actions (whisking, tempering) are exactly
  the tail DINOv2 was *not* trained to distinguish. A curation pipeline
  that reuses those embeddings will systematically under-sample the most
  informative cooking clips. Cite as motivation for training a
  cooking-specific embedding once we have any label at all.
- The YT-1B dataset itself is a copyrighted-video corpus we cannot
  legally consume. Even reproducing their result requires either the
  paper's authors' cooperation or a fully CC replacement corpus — which
  circles back to why `specint` exists.
