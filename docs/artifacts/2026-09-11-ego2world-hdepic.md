# Ego2World / HD-EPIC — turning passive cooking video into executable worlds

- **Citation.** *Ego2World: Compiling Egocentric Cooking Videos into Executable
  Worlds for Belief-State Planning*, arXiv:2605.13335 (2026). Uses HD-EPIC
  (Perrett et al., 41h across 9 kitchens, 69 recipes).
- **Also referenced.** Ego4D, Ego-Exo4D (1286h across 13 cities, of which
  ~564h are cooking), EPIC-KITCHENS, EPIC-KITCHENS VISOR, HowTo100M.

## One-paragraph summary

The paper argues that cooking is *the* canonical long-horizon,
partially-observable, multi-object domain but that existing egocentric
datasets are purely passive — you can predict the next step, you can't
try a different action and see what happens. Ego2World compiles HD-EPIC
annotations into an executable graph-transition benchmark (action
groups, reusable transition rules, per-episode world graphs, task goals)
so that LLM planners can be scored on precondition violations,
irreversible failures, and belief-state recovery. Replacing real
annotations with LLM synthesis produced a 48% hallucination rate.

## Why it matters to Specialized-Intelligence

- Confirms the mission thesis: cooking = the right stress test for
  world-model data. Every scaling axis (occlusion, irreversibility,
  language-action grounding) is present.
- All the flagship egocentric corpora (Ego4D, Ego-Exo4D, HD-EPIC,
  EPIC-KITCHENS) are gated behind consortium license forms. They are
  research-only, not "internet-scale legally accessible". This is the
  gap our repo exists to fill.
- Provides an evaluation *shape* we can adopt: score data not by "hours
  collected" but by whether it supports executable belief-state tasks
  (precondition graph coverage, irreversible-step frequency, recovery
  supervision).

## Concrete ideas to steal

- Add a `procedural_density` quality signal derived from JSON-LD
  `recipeInstructions` step count + verb variety, on top of the current
  binary `has_steps`.
- Introduce a `state_change` heuristic: presence of verbs mapped to
  known irreversible operations (fry, bake, whisk, reduce, ferment)
  scored higher than reversible ones (stir, pour, garnish).
- Add a `benchmark_shape` metric to `BenchmarkResult`: for each source,
  how many records could feed an Ego2World-style graph (has ordered
  steps AND has duration >= 60s AND declared resolution >= 480p).
- Emit optional `world_graph_stub` JSON per record so we can later diff
  our licensed corpus against HD-EPIC's semantic coverage without
  redistributing HD-EPIC media.

## Risks / gotchas

- HD-EPIC's ontology is copyrighted; we can inspire our schema but must
  not copy the action/verb taxonomy verbatim.
- "Skill" scenarios in Ego-Exo4D (cooking + music + soccer + climbing)
  are useful *generalization targets* but their license explicitly
  forbids using them to train commercial models — do NOT ingest, only
  use as evaluation-side comparisons.
