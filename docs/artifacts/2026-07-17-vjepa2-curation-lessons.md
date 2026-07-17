# V-JEPA 2 / V-JEPA 2.1 — data-curation lessons for a metadata-only crawler

- Paper: Assran, Bardes, et al., *V-JEPA 2: Self-Supervised Video
  Models Enable Understanding, Prediction and Planning*, arXiv
  2506.09985 (Jun 2025).
- Follow-up: *V-JEPA 2.1: Unlocking Dense Features in Video
  Self-Supervised Learning*, arXiv 2603.14482 (Mar 2026).
- Companion: Vo, Khalidov, et al., *Automatic Data Curation for
  Self-Supervised Learning: A Clustering-Based Approach*, arXiv
  2405.15613 (May 2024).
- Companion: Oquab et al., *DINOv2*, arXiv 2304.07193 (Apr 2023).

## Why this matters for us

V-JEPA 2 pretrains on ~1 M hours of internet video (their VideoMix22M
mix: SSv2 + Kinetics + HowTo100M + a *curated* subset of the internal
YT-Temporal-1B) and then reuses the encoder both as a
video-question-answering backbone (76.9 on TempCompass, 84.0 on
PerceptionTest) and as a latent-action world model (V-JEPA 2-AC)
capable of zero-shot Franka manipulation.

Two data-curation numbers matter for us specifically:

1. **+1.4 points average improvement** at ViT-L scale from
   cluster-based retrieval against a target distribution (Kinetics,
   SSv2, COIN, EPIC-KITCHENS) on YT-1B, vs the uncurated pool
   (V-JEPA 2 §10.2, Fig. 22 right).
2. **V-JEPA 2.1 shifted weight 3.8× *toward* YT-1B and *reduced*
   Kinetics/HowTo100M**, which cuts against the "curate hard toward
   the eval-set distribution" intuition. Their explanation: the dense
   predictive loss and multi-modal tokenizers benefit more from raw
   diversity than from concept balancing, once the encoder is big
   enough.

The takeaway is *not* "cluster retrieval always wins." It is: **cluster
retrieval is a small but reliable positive at moderate scale, and the
target distribution matters more than the algorithm.** For a
metadata-only crawler that will *never* see a 22 M-sample YT-1B, the
+1.4-point signal is a *ceiling* we should try to approach with cheap
approximations rather than the floor V-JEPA 2 claims.

## How V-JEPA 2 builds its curated set (from §10.2)

1. Extract scenes from every YT-1B video (shot boundary detection).
2. Compute an embedding per scene (their internal V-JEPA 1 encoder).
3. Run hierarchical k-means on the embeddings (following the Vo et al.
   2024 recipe: multiple levels of k-means, sampling flattens
   distribution over concepts).
4. Retrieve nearest-neighbor scenes to centroids drawn from the target
   distribution (SSv2 + Kinetics + COIN + EPIC-KITCHENS training sets).
5. Deduplicate against target *validation* sets.

## What we can borrow *today*, without GPUs or 1 M-hour storage

We do not have scene embeddings. We do have titles, descriptions, and
`recipe_steps`. A metadata proxy:

- **Target vocabulary**: check in ~200 action captions drawn from
  COIN and EPIC-KITCHENS-100 (both openly published as text). This is
  the *cheap analogue* of V-JEPA 2's target-distribution embedding
  set.
- **Candidate embedding**: TF-IDF (in pure Python, ~60 lines) over
  `title + description + " ".join(recipe_steps)`. Not as good as a
  learned encoder, but well-known to be a strong retrieval baseline
  when text is short and topical (~ MRR within 10 % of MPNet on
  cooking-title retrieval per most recent BM25-vs-dense benchmarks).
- **Retrieval**: cosine similarity to the mean target-vocabulary
  vector, or top-k centroids from k-means over the target vocabulary
  (k ≈ 20). Record `mean_similarity_on_target` per source.
- **Sanity**: verify that raising the similarity threshold trades
  yield for `mean_quality` in the expected direction. If not, kill it.

## What NOT to borrow

- **V-JEPA 2.1's raw-YT-1B tilt** — it depended on model scale
  (ViT-g) and a dense predictive loss we do not have. Do not use it
  as an argument to drop curation.
- **Frame-level shot extraction** — irrelevant until we have a raw
  media store. Metadata-level curation is the compatible slice.

## Concrete deliverable pointer

Maps to `docs/plan-2026-07-17.md` deliverable 5 (H8): implement
`quality/target_distribution.py` as the metadata proxy and add
`mean_similarity_on_target` to the additive audit payload. See H8's
success criterion.

## Falsifier

If, on the seed fixtures, ranking by target-distribution similarity
does not increase `mean_quality` per unique record vs the current
uniform-weight scorer, our metadata proxy is too weak and we should
either (a) upgrade to a checked-in fastText/HashingVectorizer, or
(b) document the negative result and abandon the direction on
metadata-only inputs.
