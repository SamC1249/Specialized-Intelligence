# 2026-06-23 — Evaluation and adversarial probes for cooking world models

Author: `Adversarial-Agent`

If we do not have a measurement, we do not have a project. This memo lists
the public 2025-2026 benchmarks we will adopt, the gaps we have to fill,
and the adversarial probes we will run on our own corpus to make sure we
are not fooling ourselves.

---

## 1. The public benchmarks we adopt

### WorldModelBench (2025)

Frontier benchmark for video-generation-as-world-model. Evaluates
**instruction following** (4 levels) and **physics adherence** (5 common
violations: object size change, mass conservation, contact penetration,
gravity, momentum). Crowd-sources 67k human labels across 14 models, then
distils into a 2B VLM judge that approximates GPT-4o accuracy.

**Why it matters for cooking:** physics adherence is the *single* hardest
property of a cooking video — water has to behave like water, dough has
to deform plausibly, fluid level has to monotonically change with
pouring. WorldModelBench gives us a standardised judge for this.

### MBench (2026)

Benchmark for **long-term memory** of video world models. Three axes:
*entity consistency*, *environment consistency*, *causal consistency*,
each split into 12 sub-dimensions. 1,040 standardised cases. Crucially
uses **trigger-conditioned scoring** — models cannot inflate their
consistency score by avoiding the actual challenge.

**Why it matters for cooking:** cooking is the prototypical long-horizon
multi-event activity. "Did the onion you set aside 30 s ago still exist?"
is exactly the entity-consistency probe we need.

### HD-EPIC VQA (CVPR 2025)

26.6k questions over the HD-EPIC corpus across 7 categories: recipes,
ingredients, nutrition, fine-grained actions, 3D perception, object
motion, gaze. Best 2025 open-source VLM (LLaVA-Video) hits 32.4%; Gemini
2.5 Pro hits 37.6%; human baseline 90.3%. **Huge headroom.**

**Use for us:** primary downstream eval. If our corpus makes a 7B VLM
move from 30% to 50% on HD-EPIC VQA, we have proven the corpus is worth
something.

### Ego2World (2026)

101 HD-EPIC videos compiled into executable graph-transition worlds, 426
goal-task instances. The first benchmark to combine real-video grounding
with hidden-world execution and explicit belief-state evaluation.

**Use for us:** the *only* benchmark that measures whether a world model
can support actual planning. If the data we produce does not move
Ego2World numbers, the data is not actually a world-model dataset.

## 2. The evaluation we have to build ourselves

The public benchmarks give us scores, but they were not designed for the
specific failure modes of cooking models. We add:

### 2.1 Cooking state-change probes

A trigger-conditioned MBench-style probe set with categories:

- **Browning / Maillard**: does the surface darken monotonically when
  heat is applied?
- **Melting**: does butter / chocolate / cheese transition from solid to
  liquid with plausible shape?
- **Mixing / emulsification**: does the boundary between two fluids
  vanish smoothly?
- **Cutting / segmentation**: does a single object become two with
  matching cross-section?
- **Phase change of water**: boil, evaporate, condense.
- **Rising / fermentation**: does dough expand monotonically over a long
  horizon?

For each category we hand-build 30-50 short clips and define the
"trigger condition" + the "expected next state". A model that cannot
produce the expected next state under the trigger fails, even if the
overall video looks plausible.

### 2.2 Contamination matrix

For every public cooking benchmark (HD-EPIC, EPIC-K, YouCook2, Ego2World,
OmniWorld-EpicKitchen subset, CookGen), compute the clip-level embedding
overlap with our discovery set. Embedding model: Cosmos-Embed1-224p.
Overlap metric: percentage of benchmark clips whose nearest-neighbour in
our corpus has cosine similarity > 0.92 (the threshold used in the VDM
memorization paper for "memorized" status). Publish the matrix in the
data card of every release.

### 2.3 License-drift audit

Re-resolve a random 1% sample of all `CC_BY` and `CC_BY_SA` source URLs
once a month. Any video whose license has changed or which has been taken
down must be flagged in the next release. This is a passive but vital
guard against license rot.

### 2.4 Memorization probes (video diffusion specific)

Following the 2025 VDM-memorization paper: pick the 1000 most-frequently-
embedded clips in our corpus and check that no fine-tuned downstream model
regurgitates them verbatim under near-prompt conditioning. The paper
shows a *trade-off* where reducing video memorization increases image
memorization in T2I-derived models — we must monitor both.

## 3. Adversarial framing of our own pipeline

Things an adversary would point out if they reviewed our day-1 plan:

1. **"Your CC-BY YouTube subset is too small to matter."** True at 2k
   transcripts (the original YouTube-Commons), maybe false at video
   scale. We have to measure the actual hour-count before committing.
2. **"Your contamination check is circular if you use Cosmos-Embed1 to
   both filter and to compute contamination."** Fair. Mitigation: use a
   *different* embedding model (SigLIP-2 or InternVideo2) for the
   contamination check than for the dedup.
3. **"Trigger-conditioned probes are easy to overfit."** Yes; we keep
   them in a held-out vault and only release the *outcomes*, never the
   clip IDs.
4. **"Open-weights VLM captioners hallucinate ingredient names."** True.
   Mitigation: cross-validate captions against ASR-derived keywords;
   downweight clips with low caption-ASR agreement.
5. **"The whole project is downstream of whether DreamDojo-style latent
   actions actually transfer."** True. Hence priority backlog item #6 in
   today's plan: a latent-action eval harness *before* we scale data
   collection.

---

## Sources

- WorldModelBench: <https://arxiv.org/html/2502.20694v1>
- MBench: <https://arxiv.org/html/2606.00793v1>
- HD-EPIC VQA (paper §5.1): <https://arxiv.org/html/2502.04144>
- Ego2World: <https://arxiv.org/html/2605.13335>
- Investigating Memorization in Video Diffusion Models: <https://openreview.net/pdf/dbda5503fa23d8315b5c73d653c7d30a5ee30677.pdf>
- Data contamination in foundation models: <https://openreview.net/pdf?id=Nsms7NeU2x>
- Ada Lovelace Institute on AI evaluation gaps: <https://www.adalovelaceinstitute.org/report/under-the-radar/>
