# WBench & WorldPrediction — what "quality" means downstream

- **WBench**: A Comprehensive Multi-turn Benchmark for Interactive
  Video World Model Evaluation. arXiv:2605.25874. 289 test cases,
  1,058 interaction turns, 22 automatic sub-metrics validated against
  human judgments. Five evaluation dimensions:
  1. Video quality
  2. Setting adherence
  3. Interaction adherence
  4. Consistency (across turns)
  5. Physics compliance
- **WorldPrediction**: A Benchmark for High-level World Modeling and
  Long-horizon Procedural Planning. arXiv:2506.04363. Sources: COIN,
  CrossTask, EgoExo4D, EPIC-KITCHENS-100, IKEA-ASM. Horizon
  `T ∈ {3..10}` for procedural planning tasks.

## Why it matters for a data-collection system

We build corpora to *feed* systems that get scored on WBench-like
axes. Our metadata quality scoring should trace back to these axes,
even indirectly:

| Downstream axis     | Corpus proxy today                       | Gap                                             |
| ------------------- | ---------------------------------------- | ----------------------------------------------- |
| Video quality       | `_score_resolution`                      | No motion / stability signal.                   |
| Setting adherence   | Keyword coverage of scene                | No scene-diversity distribution metric.         |
| Interaction adherence | Presence of `recipe_steps`             | No action-verb density metric.                  |
| Consistency         | -                                        | Requires multi-shot alignment; frame-stage only.|
| Physics compliance  | -                                        | Requires motion/optical-flow; frame-stage only. |

Two of five axes are unreachable at the metadata-only tier. That's
fine — the correct response is to **make the tier boundary explicit**
in every `BenchmarkResult` (add a `tier: Literal["metadata",
"frame_sample", "full_decode"]` column) so no one confuses coverage
of the first two axes with actual world-model utility.

## Concrete hooks into this repo

1. Add `tier` to `BenchmarkResult` (schema bump).
2. Add per-axis coverage columns (`n_scene_diverse`, `n_action_verbs`,
   etc.) computed by pluggable scorers under `quality/axes/*.py`.
3. Publish a per-run `reports/coverage-<date>.json` that maps every
   record to which downstream axis its features attempt to serve.
4. Longer-term: adopt WorldPrediction's `T ∈ {3..10}` step-horizon
   framing when picking which harvested videos to promote to
   pre-training — reject records whose recipe has fewer than 3 clean
   steps because they cannot support a `T=3` horizon.

## Ego-Exo4D scoping caveat

WorldPrediction pulls from EgoExo4D. Under our current allowlist,
EgoExo4D is *not* permitted because it requires signing a bespoke
license agreement (48-hour approval, AWS creds that expire in 14
days). It is a **research-only** dataset, not a permissively licensed
one, and it is not redistributable. Any proposal to include it must
appear in a future adversarial plan with an explicit legal review; the
default is to exclude it.
