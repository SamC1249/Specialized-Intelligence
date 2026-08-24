# HD-EPIC / Ego2World — Notes

- **Source:** Perrett et al., *HD-EPIC: A Highly-Detailed Egocentric Video
  Dataset*, CVPR 2025. Project page: <https://hd-epic.github.io/site/>.
  arXiv: <https://arxiv.org/abs/2502.04144>.
- **Downstream:** *Ego2World: Compiling Egocentric Cooking Videos into
  Executable Worlds for Belief-State Planning*
  (<https://arxiv.org/abs/2605.13335>) turns HD-EPIC's dense annotations
  into an executable graph-transition benchmark for planning.

## Why this matters for us

We are **not** trying to redistribute HD-EPIC. It is a curated,
signed-license research dataset. What HD-EPIC does give us is a **target
distribution**: 41 h of unscripted kitchen activity across 9 kitchens and
69 recipes, densely annotated with:

- recipe steps (temporal spans, prep-vs-step pairs),
- ingredients + nutritional tracking as they're added,
- per-action *what/how/why* narrations,
- 3D digital twins of kitchen fixtures,
- object masks lifted to 3D bounding boxes,
- gaze fixations aligned to object take/place events.

Ego2World then compiles these into `(state, action, next_state)` triples
with hidden world state, partial observability, and replanning — exactly
the "long-horizon, multi-object, irreversible-state" regime we care
about for world-model pretraining.

## Implications for our harvester

1. **Coverage metric.** For each candidate video we harvest, we should be
   able to answer: *does its metadata suggest coverage of HD-EPIC-style
   action verbs and ingredient nouns?* This is a cheap proxy for
   procedural density — implementable today as
   `score_cooking_verbs` using HD-EPIC's public verb list as a seed.
2. **Leakage check.** If we ever bring in Creative-Commons EPIC-KITCHENS
   Overview clips, they must be flagged so downstream evaluation on
   HD-EPIC's benchmarks isn't contaminated. Add a `known_eval_set`
   provenance bit.
3. **Complementarity, not replacement.** HD-EPIC is exocentric-poor and
   home-kitchen-only. Our web crawl should over-index on
   *counterexamples*: restaurant kitchens, non-Western cuisines,
   outdoor cooking, third-person tripod footage. Measure this
   explicitly with an entropy-of-authors and an entropy-of-title-tokens
   diversity metric per crawl-day.
4. **Executable-world direction.** Even if we never annotate to
   HD-EPIC's density, we can pre-extract JSON-LD `HowToStep` sequences
   from recipe pages that carry a compatible video — this gives us a
   text-side "world graph" cheaply, and Ego2World shows the value of
   converting passive annotations into planning-shaped structure.

## What NOT to do

- Do not fine-tune weights of our quality scorer *to* HD-EPIC — that
  Goodharts the target and defeats the purpose of a cross-source
  comparison.
- Do not attempt to redistribute EPIC-KITCHENS frames; the licence is
  CC-BY-NC (non-commercial), which under our schema classifies as
  `License.RESTRICTED` for training corpora that might power
  commercial systems.
