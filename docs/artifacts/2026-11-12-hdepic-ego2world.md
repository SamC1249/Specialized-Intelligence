# HD-EPIC + Ego2World

- **HD-EPIC paper:** arXiv 2502.04144. 41 h egocentric cooking video in
  9 kitchens, 69 recipes, 59 K fine-grained actions, 51 K audio events,
  20 K object movements, 37 K 3-D-grounded object masks, 263
  annotations/min of unscripted footage.
- **Ego2World paper:** arXiv 2605.13335. Compiles HD-EPIC into executable
  symbolic worlds with hidden-state and graph-transition rules, 101
  videos → 9 130 compiled action groups, 426 goal tasks, 155 executable
  action types; agents plan over a *belief graph* under partial
  observation.
- **Licence of the data itself:** University of Bristol research licence
  (non-redistributable). We cannot host or mirror the videos.

## One-line summary

HD-EPIC is the current gold standard for *procedurally dense, 3-D-grounded,
in-the-wild* cooking video. Ego2World is the current gold standard for
turning that data into a *world model evaluation harness* with belief
updates.

## Why it matters to us

- **Defines the target distribution.** We are not trying to reproduce
  HD-EPIC's annotations; we are trying to find *publicly re-distributable*
  video whose *content statistics* resemble HD-EPIC's (dense actions per
  minute, multi-object manipulation, state changes, long horizons).
- **Belief-state evaluation (Ego2World) is a quality rubric for training
  data.** A dataset is "good for world models" iff a policy trained on it
  can update belief under partial observation. We cannot reproduce Ego2World
  directly (their data is restricted), but we can *mirror the axes*:
  - action density per minute (proxy: `len(recipe_steps) / duration_min`)
  - unique object mentions (proxy: tokenised nouns in title + description +
    recipe steps)
  - partial observability (proxy: first-person vs third-person; Common
    Crawl recipe videos are overwhelmingly third-person, HD-EPIC is
    egocentric → we are structurally missing the egocentric slice).
- **Egocentric gap.** All four of our seed sources skew third-person.
  Legally-clean *egocentric* cooking is extremely rare on the open web.
  This is a research question in itself; see the open question in the
  next-plan section.

## What we can / can't copy

- **Can:** The *annotation schema* (action, object, state change triples)
  and the Ego2World belief-graph evaluation framework (if we ever ship a
  training run, we can score it against an Ego2World-style held-out
  symbolic world).
- **Can't:** Any pixels or annotations from HD-EPIC. The licence
  explicitly restricts redistribution.

## Concrete actions

1. Add an `action_density_proxy` to `quality/metrics.py` as part of H4.
2. Open a `docs/plan-*.md` item (next plan) tracking "legally-clean
   egocentric video" as its own research sub-problem — candidate sources:
   Wikimedia Commons POV files (search `pov OR "first person" cooking`),
   Blender Institute shorts, GoPro community CC uploads on Vimeo (ToS-
   checked), Archive.org home-movies collection.
3. Record both papers in `docs/artifacts/` so future plans don't re-derive
   the egocentric-gap finding from scratch.
