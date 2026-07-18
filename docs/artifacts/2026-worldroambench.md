# WorldRoamBench (ArXiv 2606.31672, 2026)

> "An Open-World Benchmark for Long-Horizon Stability of Interactive
> World Models."

## What it claims

Interactive world models routinely fail at **memory** and
**interaction-physics** dimensions that trajectory-level metrics hide.
WorldRoamBench evaluates four axes:

1. **Action following** (per-frame, not just start-vs-end).
2. **Vision drift** (segment-based, catches non-monotonic collapse).
3. **Physics plausibility** (controllability-gated).
4. **Memory** (scene memory via 3D reconstruction, subject memory via
   tracking + VLM reasoning).

10–60s continuous interaction across 600+ open-domain scenes; no
current model reliably clears all four.

## Why this matters for us

We ship metadata-only quality scoring today. WorldRoamBench tells us:

- **Duration alone is not the right axis.** A 60s continuous
  single-shot cooking sequence is far more valuable than a 5min video
  with jump cuts. Our scorer cannot detect edit cuts from metadata, but
  we *can* penalize records tagged `type=montage` on Commons or with
  `videoDefinition=sd` on IA — a weak proxy for hobbyist single-shot
  vs edited broadcast.
- **Memory eval implies long-horizon dependence.** Corpus construction
  should prefer many short (10–60s) *continuous* clips over few very
  long compilations.

## What we did not ship yet

A `single_shot_probability` metric would require either:

- Access to keyframe metadata (not exposed by any of our current APIs).
- Actual video download and shot-boundary detection (out of scope).

Written down here so the next Adversarial-Agent can attack it.
