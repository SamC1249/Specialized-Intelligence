# V-JEPA 2 / V-JEPA 2.1 — Cluster-based retrieval curation for video pretraining

> Source: Assran et al., "V-JEPA 2: Self-Supervised Video Models Enable
> Understanding, Prediction and Planning" (arXiv 2506.09985, June 2025);
> Bardes et al., "V-JEPA 2.1: Unlocking Dense Features in Video
> Self-Supervised Learning" (arXiv 2603.14482, 2026).
> Notes captured: 2026-06-24 by Adversarial-Agent.

## TL;DR

V-JEPA 2 builds **VideoMix22M** (22M samples, ~1.6M video-hours) by
mixing five sources with hand-tuned weights:

| source             | role                          | rough weight (VM22M / VM163M) |
|--------------------|-------------------------------|--------------------------------|
| YT-Temporal-1B     | uncurated YouTube ("YT1B")     | 0.188 → **0.720**             |
| Kinetics-400/600/700 | exo-centric action curation | medium                         |
| HowTo100M          | tutorial videos                | medium                         |
| Something-Something v2 | ego/manipulation             | 0.056 → 0.170                 |
| ImageNet (then LVD-142M in 2.1) | static appearance     | low                           |

YT1B is filtered with a **cluster-based retrieval pipeline** (adapted from
Oquab et al.'s DINO-v2 image curation): extract scenes → embed → assign to
clusters → resample to match a target distribution composed of *Kinetics +
SSv2 + COIN + EPIC-KITCHENS train sets*.

V-JEPA 2.1 scales that mixture to **VisionMix163M** (~163M samples), uses
LVD-142M for images, doubles down on YT1B (0.188 → 0.720) and SSv2 (×3.0),
and adds dense / hierarchical self-supervision. ViT-G/16 with 2B params.

## Why this matters to *our* flywheel

We cannot reuse VideoMix22M directly: YT1B is YouTube acquisition, which
is **out of scope** for us (see `legal-landscape.md`, decision
`D-2026-06-20-1`).

But the *curation recipe* is independently useful:

1. **Pick a target distribution.** The Meta team uses Kinetics + SSv2 +
   COIN + EpicKitchens train as the "what good looks like" seed. We can
   pick license-clean seeds (Wikimedia cooking category + Internet
   Archive Prelinger + a curated CC PeerTube subset) and use those as the
   target distribution for filtering any larger noisy pool.
2. **Cluster-and-resample over a noisy pool.** Once we have a target,
   we can filter *any* candidate corpus (Common Crawl WAT-extracted
   `<video>` URLs, Wikimedia bulk dumps, the long tail of Internet
   Archive uploads) by cluster membership instead of by classifier
   confidence. This generalises beyond cooking.
3. **Motion-rich resampling.** V-JEPA 2.1 upweighting SSv2 by 3× to
   bias toward motion is consistent with our day-one prior that
   *aesthetic-only quality is misleading for world-model utility.*

## Adversarial notes

- Their filtering still **starts from a 1.4M-hour YouTube pool.** Without
  that, the comparable result for us depends on how good our seed
  distribution is. *Hypothesis to test: a CC-only seed of ~50 hours plus
  ~500 hours of mixed Wikimedia + IA cooking is sufficient to drive
  retrieval into Common Crawl video URLs and recover meaningful diversity.*
- Their evaluation suites (EK100, SSv2, Diving48, MVP) are all CC-BY-NC.
  We **cannot use those for downstream commercial probes**. We need a
  license-clean held-out probe set, e.g. a Wikimedia split with
  hand-labelled actions, before we can directly compare against the
  V-JEPA 2 numbers.
- LVD-142M is itself a curated subset of public web images. We should
  index whether LVD-142M's curation method (centroid retrieval against
  curated seeds) is replicable on Common Crawl for *video keyframes*,
  which would feed our same pHash + embedding pipeline.

## Concrete actions for our repo

1. **New `components/curation/cluster_retrieval.py` (planned).** Stub for
   k-means/HNSW-based selection of candidates against a seed target.
   Operates on embeddings (CLIP / V-JEPA-encoded). Pure metadata, no
   bytes.
2. **New `docs/research/seed-target-distribution.md` (planned).**
   Document our proposed CC-clean seed set: counts, hours, cuisine /
   language / kitchen-geography breakdown. Inform on what is realistic.
3. **Eval-set decontamination is mandatory.** V-JEPA 2 explicitly
   excludes validation-set videos from the uncurated pool. Our equivalent
   is `components/eval_blocklist.py` (added today) + the
   `eval_blocklist.jsonl` we maintain per benchmark we care about.
4. **Provenance.** V-JEPA 2's data-card includes per-source counts and
   weights. We replicate this in `db_structured.md` §7 (planned bump).

## Key references

- arXiv 2506.09985 — V-JEPA 2 paper (sections 3 "Pre-training", 4 "Data
  Curation Pipeline", Table 1 source weights).
- arXiv 2603.14482 — V-JEPA 2.1 paper (Table 3 dataset comparison,
  Section 4 "Pretraining Data").
- Oquab et al., DINOv2 (arXiv 2304.07193) — the underlying cluster-based
  retrieval recipe.
- Zellers et al., "MERLOT" / YT-Temporal-1B (arXiv 2201.02639).
