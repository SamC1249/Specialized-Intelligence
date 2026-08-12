# Artifact — Ego4D Goal-Step (NeurIPS 2023)

**Date filed:** 2026-08-12
**Filed by:** Adversarial-Agent
**Primary URL:** <https://papers.neurips.cc/paper_files/paper/2023/file/7a65606fa1a6849450550325832036e5-Paper-Datasets_and_Benchmarks.pdf>
**Cited in plan:** `docs/plan-2026-08-12.md` (H4)

## One-sentence summary

Ego4D Goal-Step is the largest publicly annotated *procedural* video
dataset in cooking-adjacent activities: **2,807 hours of goal-level
annotation over 7,353 videos**, plus a fine-grained cooking-only
subset of **430 hours / 48K step segments / 86 goals / 514 substeps**
— giving us a target density (~23 step segments per activity /
~32.5s per step) that our metadata scorer should approach.

## Why it matters to us

- Ego4D itself is *not* redistributable under our constraints, but
  its **annotation density is the aspirational ceiling** for how a
  well-tagged recipe page should look. When we score a page's
  `recipe_steps` list, "≥10 steps averaging 5–60s of implied action
  each" is a defensible cutoff.
- The paper defines **step-taxonomy discovery** iteratively (16
  annotation iterations, 8 substep). Our system should keep taxonomy
  extension in mind — the `keywords` field is the seam for future
  cluster labels.
- Cooking is the largest sub-scenario (~72% of Ego4D). This validates
  our narrow target: if you had to pick one activity as the entry
  point, this is it.

## Ideation — how it changes what we ship

1. **Procedural density metric.** Extend `quality/metrics.py` with a
   `procedural_density` component defined as
   `min(1.0, len(recipe_steps) / target)` where `target = 10`
   (approx. half of Ego4D's per-activity density). Deferred to a
   future coding sprint, but the target `target=10` is
   evidence-based, not arbitrary.
2. **Substep expansion.** Recipe pages often have compound
   `HowToStep.text` values (e.g. "Mince the garlic and sauté for 30
   seconds"). A future extractor should split on `.` /`;` /`,` +
   verb-classification to approximate Ego4D's substep granularity.
3. **Cross-source join.** If we later index HowTo100M metadata (URLs
   only, per its license), a URL cross-hit against Ego4D Goal-Step's
   scenario taxonomy is a cheap proxy for "this recipe URL likely
   maps to a well-known procedural activity."

## Risks

- Ego4D has a research-only license. We never redistribute frames
  from it. We are permitted to cite its statistics.
- Their step-count histogram is fat-tailed. A hard cutoff on
  `recipe_steps` under-serves both very-short (dessert) and
  very-long (BBQ, sourdough) recipes.
