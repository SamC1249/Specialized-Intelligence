# V-JEPA 2 and VideoMix22M: What a frontier "video world model" actually eats

- Paper: *V-JEPA 2: Self-Supervised Video Models Enable Understanding,
  Prediction and Planning* (Meta FAIR, arXiv:2506.09985, June 2026).
- URL: https://arxiv.org/abs/2506.09985
- Companion post: https://ai.meta.com/research/vjepa/
- License of the artefact: the model + code are released; the pretraining
  corpus is a **union of upstream datasets**, each under its own terms.

## The composition of VideoMix22M (VM22M)

| Component            | Style                        | Rough licence posture                 |
| -------------------- | ---------------------------- | ------------------------------------- |
| Something-Something v2 | Egocentric hand-object      | Research / non-commercial              |
| Kinetics 400/600/700  | Exocentric human action     | CC-BY-4.0 (per YouTube uploader)      |
| HowTo100M             | YouTube instructional        | Uploader-dependent; not redistributable |
| YT-Temporal-1B (YT1B) | Uncurated YouTube           | Uploader-dependent; not redistributable |
| ImageNet              | Still images (temporal dupe) | Research licence                       |

Total: 22M samples, > 1M **hours** of video, sampled with per-source
weights that were tuned manually. A ~62-hour Droid tail is used
downstream for the action-conditioned V-JEPA 2-AC head.

## Frontier lessons for a legally-clean crawler

1. **Weighted mixtures beat "just concatenate."** V-JEPA 2's ablations
   show manually-tuned per-source weighting outperforming uniform
   concatenation. Our `run_comparison` returns per-source rows but has no
   notion of a *mixture recipe*. We should add a `MixtureRecipe` that
   takes `{source_slug: weight}` and reports the *expected* corpus
   quality if we sampled with those weights.

2. **Ego-centric procedural tasks are the frontier.** VJEPA-2's headline
   metric is Something-Something v2 (77.3 top-1) and Epic-Kitchens-100
   anticipation (39.7 R@5). Both are hand-object, procedural, egocentric
   — exactly the modality cooking video sits in. Our roadmap should
   privilege sources that surface egocentric procedural clips even if
   they are *smaller* than exocentric collections.

3. **Uncurated is a first-class strategy.** YT1B is explicitly "1.4M
   video-hours with no curation." The engineering choice is to *keep the
   candidate pool wide and filter late*. Our current pipeline filters
   early (adapter refuses non-video mime types before scoring). We should
   log rather than drop: adapters yield everything, `quality.rules`
   decides tier.

4. **Small aligned data is the value-multiplier.** 62h of unlabeled robot
   video, added to 1M+ hours of self-supervised video, unlocked zero-shot
   robot planning. In cooking-video terms: our procedural signal
   (recipe_steps, ingredient text) is the analogue of "action labels" on
   top of raw video. Even sparse presence dramatically increases downstream
   utility. **Concretely**: procedural_density should be a scalar tracked
   in `BenchmarkResult`, not just folded into `mean_quality`.

## What we should not copy

- Do not adopt HowTo100M or YT1B directly. Uploader licences are
  uncontrolled; the resulting corpus is not redistributable. We only
  admit YouTube listings with `videoLicense=creativeCommon` **and**
  `contentDetails.licensedContent==false`, per the memory landmine.
- Do not treat scale as an end in itself. VJEPA-2 shows scaling curves
  saturate for smaller (~1B) encoders; our comparative advantage is
  *quality per legal hour*, not raw hour count.
