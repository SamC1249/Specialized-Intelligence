# 0002 — HD-EPIC and Ego2World: what "world-model-ready" video looks like

- Sources:
  - Perrett et al. *HD-EPIC: A Highly-Detailed Egocentric Video
    Dataset.* arXiv:2502.04144, CVPR 2025.
  - *Ego2World: Compiling Egocentric Cooking Videos into Executable
    Worlds for Belief-State Planning.* arXiv:2605.13335, 2026.
- Reviewed: 2026-08-26 by Adversarial-Agent.

## What are they?

**HD-EPIC** is 41 hours of unscripted egocentric cooking video across 9
kitchens and 69 recipes with layered annotations: recipe steps,
fine-grained verb-noun actions, moving-object 3D tracks, gaze, audio
events, and a Blender digital twin of every kitchen.

**Ego2World** takes HD-EPIC's annotations and *compiles them into an
executable environment* (world graph + transition rules + belief
states) so agents can act inside a real kitchen replay.

## Why they matter for us

They define the **downstream target function** for our data collection.
A world-model-training dataset is only as good as the fraction of its
hours where the following signals survive:

- **Long-horizon state** — a pot moving from stove → sink → drying rack
  across 10 minutes.
- **Irreversible transitions** — cracked egg, cut vegetable, boiled
  water.
- **Language grounding density** — narration or subtitles that name
  actions and objects at ≥ 1 event / 10 s.
- **Camera stability** — first-person or a fixed-tripod third-person
  view, not shaky-handheld cutaways.

None of these are captured by our current metadata-only scorer. That's
a gap adversarial-agent should push against.

## Implementation ideas for `specint`

1. **World-model-signal proxy features** we can compute from metadata
   *before* downloading anything:
   - `has_subtitle_track`: from Wikimedia `<track>` tags, PeerTube
     `captions` API, or Archive.org `.srt`/`.vtt` files listed in the
     item metadata.
   - `narration_density_s`: subtitle events per second, an
     interpretable stand-in for "instructions per unit time".
   - `single_scene_hint`: a boolean from title/description
     heuristics — a video titled *"How to make pasta — one-take,
     no cuts"* is much more likely to be world-model-usable than
     *"10 fastest recipes 2026 (compilation)"*. Regex against known
     compilation/short-form patterns and penalize.
   - `pov_hint`: keywords like `pov`, `first-person`, `egocentric`,
     `gopro` add a small positive weight.
2. **Downstream utility label** on the fixture set.
   Hand-label the 8 records currently in `tests/fixtures/*/` with a
   ternary `world_model_utility ∈ {no, maybe, yes}` and store it in
   `tests/fixtures/utility_labels.json`. Add a
   `tests/test_quality_calibration.py` that computes rank
   correlation (Spearman) between `quality_score` and these labels
   and **fails CI if ρ drops below the last committed threshold**.
   This is the first honest signal we'll have about whether our
   scoring is measuring anything real.
3. **Executable-world compatibility flag**. Not every legally-clean
   video is worth curating for world-modeling. Add a
   `quality/executability.py:score_executability(record)` that
   requires at least: `duration_s ≥ 120`, `pov_hint ≥ 0.5`,
   `narration_density_s > 0`, and non-empty `recipe_steps` OR
   subtitles. Emit as a separate scalar in `BenchmarkResult`
   (`mean_executability`) so we can compare against the general
   `mean_quality`.

## Benchmark row that would prove it

After ranking by `quality_score`, we should see the top-decile
records match the ternary utility labels ≥ 80% of the time (baseline
random = 33%). If not, the scorer is decorative.

```
metric                             value  target
spearman(quality, utility_label)   ?      ≥ 0.5
top10%_precision_yes               ?      ≥ 0.8
top10%_recall_yes                  ?      ≥ 0.3
```

## Constraints & risks

- HD-EPIC and Ego2World themselves are research-only downloads with
  data-use agreements; we do not re-host them. Their **methodology and
  utility labels** are what we borrow.
- Hand-labeling 8 fixture records is not statistically significant.
  This calibration test is a smoke alarm, not a validator; the real
  calibration will need a checked-in labeled set of ≥ 200 records
  (future Coding-Agent PR).
