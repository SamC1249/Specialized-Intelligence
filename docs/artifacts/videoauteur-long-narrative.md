# VideoAuteur — long-narrative cooking video generation

- **Paper:** Xiao et al., *VideoAuteur: Towards Long Narrative Video
  Generation*, ICCV 2025.
  <https://openaccess.thecvf.com/content/ICCV2025/html/Xiao_VideoAuteur_Towards_Long_Narrative_Video_Generation_ICCV_2025_paper.html>

## What it is

ICCV 2025 paper that introduces a large-scale cooking video dataset
**specifically designed for long-form narrative generation** — i.e.,
multi-shot, event-coherent recipes rather than 4-second clips. Uses a
"Long Narrative Video Director" to align visual embeddings across
shots. Code + data promised as public release.

## Why it matters for Specialized-Intelligence

Directly justifies weakness **W4** in `plan-2026-08-25.md`:

> `_score_duration` peaks at 300s and decays to zero by ~1 hour. But
> the research payload we actually want for world-model training is
> the long-horizon, multi-step, irreversible segment.

The VideoAuteur pipeline explicitly needs *multi-minute, event-rich*
cooking clips. That is the mode-shift our duration curve must move
toward. If our top-quality records are 4-minute food-porn cuts,
downstream long-narrative models will underfit.

## Concrete implementation ideas

- **Duration curve redesign (W4):** log-normal peaking at 600s with a
  gentle tail out to 45 minutes. Concretely:
  `score = exp(-((log(d) - log(600))^2) / (2 * sigma^2))` with
  `sigma = 0.8`. Ship it under a `SCORER_VERSION` flag, run the
  harness with old + new versions on the same fixtures, commit both
  reports to `reports/`, then flip the default only after the
  regression test is re-baselined.
- **Multi-shot heuristic (metadata only):** count colon- or
  digit-prefixed step lines in `description` / `recipe_steps`; a
  video with N ≥ 5 steps is more likely to be a multi-shot recipe
  than a single-take demo. Add as a new component with a small
  weight (0.05) so we do not upend the current ranking.
- **Cross-reference W6 (dedup):** VideoAuteur is likely to reuse
  YouTube-Commons cooking channels. Our overlap script (`W10`)
  should include it as an alternative reference besides FineVideo.
