# Artifact — HD-EPIC + Ego2World

**Date filed:** 2026-08-12
**Filed by:** Adversarial-Agent
**Primary URLs:**
- HD-EPIC (CVPR 2025): <https://arxiv.org/html/2502.04144v1>
- Ego2World (arXiv 2605.13335): <https://arxiv.org/html/2605.13335>

**Cited in plan:** `docs/plan-2026-08-12.md` (adversarial questions)

## One-sentence summary

HD-EPIC is 41 hours of unscripted kitchen egocentric video with **263
annotations per minute** (recipe steps, actions, ingredients + nutrition,
object movement, audio, 3D digital-twin), and Ego2World *compiles those
annotations* into an executable "Video-Compiled Symbolic Simulator"
that trains world-model agents on **belief graphs vs. hidden world
graphs**. This is the annotation-density and execution-target frontier
we should benchmark our raw pipeline against.

## Why it matters to us

- HD-EPIC's "annotations per minute" (263) is a **useful denominator**:
  our raw metadata-only pipeline produces on the order of tens of
  bytes of usable annotation per hour of source video. We need to
  keep this ratio in mind when we start extracting frames or ASR
  transcripts.
- Ego2World's insight is that **world-model training benefits most
  from state-transition supervision**, not just narration. Recipe
  pages usually carry ordered `HowToStep` blocks (a proxy for state
  transitions); videos without them are still valuable but should be
  ranked lower.
- Ego2World compiles from HD-EPIC's *symbolic* annotations, not from
  raw pixels. This is a strong argument for treating recipe-text
  metadata as first-class signal — which is exactly what our
  `has_steps` and future `procedural_density` metrics do.

## Ideation — how it changes what we ship

1. **State-transition candidate score.** Rank recipe pages by the
   count of imperative verbs in `recipe_steps` (proxy for action /
   state-change events). Deferred, but the plumbing exists (we
   already store `recipe_steps: list[str]`).
2. **Multi-modal alignment target.** For every video record we should
   *eventually* attach a text description that is aligned to the video
   timeline. Today we accept whatever the source gives us; tomorrow
   we should require it.
3. **Belief vs. hidden state proxy.** For pretraining we don't need
   Ego2World's simulator, but the *task pattern* — "predict the next
   step given a partial belief" — is exactly what a well-tagged
   recipe page supports out of the box.

## Risks

- HD-EPIC and Ego2World are academic artifacts; we do not
  redistribute them. Citations only.
- The 263-annotations/min benchmark is a controlled-lab number.
  Real web recipes have 5–30 imperative verbs per page. That is
  still 2–3 orders of magnitude sparser than HD-EPIC — but the
  scale advantage of web-crawlable recipes makes the trade defensible.
