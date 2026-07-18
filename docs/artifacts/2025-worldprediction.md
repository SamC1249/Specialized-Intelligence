# WorldPrediction (ArXiv 2506.04363, 2025)

> "A Benchmark for High-level World Modeling and Long-horizon
> Procedural Planning."

## What it claims

Existing world-model evaluations focus on **low-level** visual
continuity (does frame N+1 look plausible given frame N). WorldPrediction
argues the *actually hard* task is **high-level procedural planning**:
given initial and final world states, pick the right *sequence of
abstract actions*. Their discriminative task uses "action equivalents"
(same abstract action in different scenes) as distractors to prevent
models from cheating via low-level continuity. Reported result: frontier
models score ~57% on state prediction and only ~38% on planning; humans
solve both perfectly.

## Why this matters for our data collection

The signal that separates a mediocre cooking clip from an *excellent
world-model training example* is not resolution. It is **procedural
density** — how many distinct, state-changing actions per second, and
how legible are those state changes in the metadata.

Concrete implication for our quality scorer:

- **High-value.** A 4-minute video with 12 recipe steps and titles like
  "chop, sauté, deglaze, reduce, plate" is worth more than a 4-minute
  video with 1 step and title "family dinner".
- **Metadata-only proxies.** We cannot watch every video pre-selection.
  But we *can* count recipe steps (Commons+Common Crawl both expose
  these), verb-like tokens in title/description, and time/temperature
  literals ("simmer 20 minutes", "350 °F").

## What we shipped

`src/specint/quality/metrics.py::_score_procedural_density` — counts
step entries, imperative-verb candidates (short lowercase tokens
matching a small allowlist), and time/temperature regex hits. Weighted
into the overall score. See test_quality.py for exact bounds.

## Deliberately not adopted

- Actual state-transition discrimination requires video decoding.
  Deferred until we have a media-download pipeline that respects
  license clearance.
