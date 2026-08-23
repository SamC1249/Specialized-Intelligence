# Ego2World — HD-EPIC as an executable world benchmark (arXiv 2605.13335)

- **Citation:** *Ego2World: Compiling Egocentric Cooking Videos into
  Executable Worlds for Belief-State Planning.* arXiv 2605.13335, v1
  (May 2026).
- **Permalinks:**
  - HTML: <https://arxiv.org/html/2605.13335v1>
  - PDF: <https://arxiv.org/pdf/2605.13335>

## One-paragraph summary

Ego2World does not release new raw video. It ingests the dense per-frame
annotations of the HD-EPIC dataset (41 hours, 9 kitchens, 69 recipes) and
compiles them into an **executable layer**: primitive actions →
semantically coherent action groups → reusable graph-transition rules →
episode-level world graphs with hidden state, functional areas, symbolic
object states, executable skills, and goal-task specifications. The
resulting benchmark (101 videos, 9 130 action groups, 426 goal tasks,
155 executable action types) lets agents *act, receive feedback, and be
scored on belief-state trajectories under partial observation* — a much
stronger evaluation than passive next-frame prediction. Ablations show
that replacing real annotations with LLM-synthesised environments yields
significantly less realistic layouts and action orderings; the *real
naturalistic annotations* are load-bearing.

## Transferable to `specint`

- **Schema extension.** `VideoRecord` today captures URL + metadata +
  optional `recipe_steps`. A follow-on record type — call it
  `ExecutableAnnotation` — should capture (a) normalised primitive
  action, (b) start/end timestamps, (c) object references, (d) declared
  state pre/post. Even a text-only stub is enough to run comparability
  against Ego2World's action-group taxonomy.
- **Comparison metric.** Add an `action_density` per-source metric
  (actions per minute inferred from `recipe_steps` count / declared
  duration) to `src/specint/quality/metrics.py`. It is a cheap, purely
  metadata-only proxy for procedural richness.
- **Dataset target.** Ego2World's 155 executable action types form a
  natural *coverage vocabulary*. `python -m specint transparency`
  should be able to report "of the 155 canonical actions, our clean
  corpus covers N with ≥K demonstrations each."
- **Adversarial goal.** Beat HD-EPIC on *hours of legally-clean
  procedural cooking video with dense step text*. HD-EPIC is CC-BY-NC
  4.0 (not redistributable for training beyond research). We need a
  redistributable equivalent.

## NOT transferable

- HD-EPIC itself is **CC-BY-NC-4.0** — non-commercial only. We do not
  ingest its raw video or annotations. Only its *taxonomy* is fair game
  as a benchmarking rubric.
- Ego2World's compilation pipeline assumes rich professional
  annotations that the open web does not have. We would need to *emit*
  such annotations from a VLM pipeline (see DenseStep2M).

## Adversarial notes

1. The paper's central claim is that real-annotated environments beat
   LLM-synthesised ones. If true, our corpus is worth strictly more
   when it carries dense per-clip step text than when it does not — so
   the `quality/text_density` weight is probably under-tuned.
2. 41 hours is *tiny*. Any legal-source pipeline that yields >50 hours
   of dense-step cooking video is immediately competitive as a raw
   input to an Ego2World-style compiler.
