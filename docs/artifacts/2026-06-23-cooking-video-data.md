# 2026-06-23 — Cooking video datasets and world models

Author: `Adversarial-Agent`

This note inventories the public corpora and frontier world-model papers
that are relevant to a cooking-video data play, and extracts what we should
copy, what we should avoid, and what we should *not* re-do.

---

## 1. EPIC-KITCHENS-100 + HD-EPIC (Damen group, Bristol)

- **EPIC-KITCHENS-100**: 100 h of head-mounted-camera, unscripted, native-
  environment cooking video across 45 kitchens, 700 videos, 90k action
  segments, multi-language narration. The de-facto benchmark for fine-
  grained egocentric action.
- **HD-EPIC** (CVPR 2025): 41 h of *multi-day* unscripted recordings of
  69 recipes across 9 kitchens, with **3D digital twins** of every kitchen
  fixture, fine-grained per-action narration, 50.9k audio events, 7.7M
  hand masks, gaze priming, and a 26.6k-question VQA benchmark spanning
  recipes, ingredients, nutrition, fine-grained actions, 3D perception,
  object motion and gaze. Best open-source video VLM today (Gemini) hits
  37.6% on the VQA; the human baseline is 90.3%.
- **EPIC-Sounds, EPIC-Fields, VISOR**: derived audio, 3D camera, and
  pixel-mask layers on the same video substrate.

**What we copy:** the *interconnected annotation philosophy* — every clip
gets multiple layers of supervision (action, mask, audio event, 3D camera,
gaze) that can be cross-validated.

**What we do not re-do:** the actual EPIC video bytes. Those are licensed
for academic research only; we cannot rebuild a corpus on top of them.
EPIC is a benchmark for us, not a training source.

## 2. YouCook2, HowTo100M, CookGen / VideoAuteur

- **YouCook2**: 2k third-person YouTube cooking videos across 89 recipes,
  176 h total, dense procedural-step temporal segments.
- **HowTo100M**: 1.2M YouTube how-to videos with raw ASR. Widely used,
  but the ASR is notoriously misaligned and noisy.
- **CookGen / VideoAuteur** (2025): re-curates HowTo100M + YouCook2 into
  30-150 s narrative videos, 4-12 clips each, with high-quality VLM
  captions (GPT-4 + a fine-tuned video captioner).

**What we copy:** the *segmentation granularity* (30-150 s parent video,
5-30 s clip, 4-12 clips/video) is a sweet spot for procedural learning.

**What we avoid:** GPT-4-as-captioner. We want fully open-weights, both
for cost and for license cleanliness.

## 3. Ego2World (2026)

Compiles HD-EPIC into **executable symbolic worlds** with graph-transition
rules. 101 videos, 9.1k action groups, 426 goal-task instances, 155
normalized action types. Key insight: action-overlap scores *overestimate*
physical-state success; persistent belief memory improves completion.

**Implication for us:** raw video pretraining is not enough. We need to
either (a) emit per-step symbolic state alongside video clips, or (b) be
able to *derive* it after the fact. This is R2 in today's plan.

## 4. OmniWorld (ICLR 2026)

Multi-domain, multi-modal dataset for 4D world modelling. Aggregates and
re-annotates EPIC-Kitchens, Ego-Exo4D, HOI4D, DROID, RH20T, AgiBot,
CityWalk, and a synthetic OmniWorld-Game subset. Adds depth, camera pose,
text, optical flow, foreground masks.

**Implication for us:** the *re-annotation* path is the high-value one.
Existing video bytes are already collected; we are competitive only if our
*labels* are denser or our *license trail* is cleaner.

## 5. DreamDojo (NVIDIA, ICML 2026)

44,711 h of egocentric human video → foundation world model → post-train
on small robot dataset → distill to ~10 FPS autoregressive inference.
The key trick is **continuous latent actions** as a proxy for the
missing action labels in raw human video.

**Implication for us:** if the latent-action trick works at 44 kh, it
should work at our target of 5-10 kh of *cleaner* video. We should plan
a latent-action evaluation harness as one of the very first eval probes.

## 6. Sekai (2026)

5,000+ h of walking + drone videos across 750 cities, annotated with
location, weather, camera trajectory. Useful as a *template* for what a
modern, niche-but-rigorous video corpus looks like.

**Implication for us:** the right annotation set for *cooking* is the
analogue of `(location, weather, camera_traj)`: probably `(recipe_id,
ingredient_set, kitchen_layout, camera_view, time_of_day, cuisine)`.

## 7. YouTube-Commons (Pleias, 2024)

2.06M YouTube videos under CC-BY, with metadata + transcripts +
attribution. *Currently transcripts only — no video bytes.* This is
exactly the licence posture we need; the gap is that nobody has extended
this to the *video* side at scale yet. That gap is an opportunity.

---

## How this changes the project plan

1. We will not re-collect EPIC-Kitchens / HowTo100M video bytes.
2. We will use EPIC-Kitchens / HD-EPIC / YouCook2 *only as evaluation
   sets*, and we will measure contamination against them on every release.
3. The *training* corpus is built from CC-BY YouTube (via the Data API,
   with `videoLicense=creativeCommon`), CC Vimeo, PeerTube, Archive.org
   cookery shows, and Wikimedia Commons cooking videos.
4. Our differentiator is the annotation layer (procedural steps + object
   states + recipe grounding) and the license trail, not the raw bytes.
5. We adopt the OmniWorld philosophy: per-clip multi-modal label set with
   a clear `🙂 / ✅ / ❌` provenance flag per modality.

---

## Sources

- HD-EPIC paper: <https://arxiv.org/html/2502.04144>
- EPIC-KITCHENS challenge & dataset: <https://epic-kitchens.github.io/2026>
- EPIC-KITCHENS-100 (IJCV 2022): <https://link.springer.com/article/10.1007/s11263-021-01531-2>
- OmniWorld dataset card: <https://huggingface.co/datasets/InternRobotics/OmniWorld>
- Ego2World project page: <https://sj-li.com/PROJ/Ego2World/>
- Ego2World arxiv: <https://arxiv.org/html/2605.13335>
- DreamDojo paper & code: <https://github.com/NVIDIA/DreamDojo>
- DreamDojo summary: <https://www.luigifreda.com/2026/02/20/dreamdojo-scaling-robot-world-models-with-44000-hours-of-egocentric-human-video/>
- YouCook2: <http://youcook2.eecs.umich.edu/>
- VideoAuteur / CookGen: <https://videoauteur.github.io/>
- YouTube-Commons (HF dataset card): <https://huggingface.co/datasets/pshishodia/YouTube-Commons>
- YouTube-Commons blog: <https://huggingface.co/blog/Pclanglais/youtube-commons>
