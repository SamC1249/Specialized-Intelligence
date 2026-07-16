# YouCook2 (Zhou, Xu, Corso — AAAI 2018)

- Paper / project: http://youcook2.eecs.umich.edu/
- Dataset readme: http://youcook2.eecs.umich.edu/static/YouCookII/youcookii_readme.pdf

## Claim

2,000 untrimmed third-person cooking videos across 89 recipes; each
video is manually annotated with temporal step boundaries and one
English imperative sentence per step ("grill the tomatoes in a pan").
Total 176 hours, average 5.26 minutes per video, 3–16 steps per
recipe. Sourced from YouTube — same licensing wall as HowTo100M.

## Evidence

- Distinguishes itself from Breakfast, MPII, 50Salads by scale +
  imperative English annotation.
- Later COIN (Tang et al., CVPR 2019) generalises the same setup to
  180 tasks across 12 domains (11,827 videos) with the same three-
  level domain→task→step ontology.
- Both YouCook2 and COIN annotations are human-labelled — this is the
  gold standard we compare our metadata-only heuristics against.

## Steal

1. **Use the YouCook2 recipe list (89 dishes) and COIN cooking-domain
   steps as a *gold seed set* for our procedural-density heuristic.**
   If our Common Crawl adapter is doing its job, it should discover
   Recipe JSON-LD blocks whose `recipeInstructions[]` count matches
   YouCook2's step count for the same dish within ±2 on average. Add
   a comparison bench once we have a Wikibooks Cookbook fixture.
2. **5-minute duration target confirmed empirically.** Our current
   `_score_duration` peaks at 300s and decays out to ~1h — matches
   YouCook2's average of 5.26 min. No change to the constant, but the
   choice now has an external anchor to cite in the module docstring.
3. **Steps-per-minute is the right procedural-density unit.**
   YouCook2 has ~2 steps/min on average. Our new `procedural_density`
   component in `quality/metrics.py` should normalize to that scale
   (steps/min ∈ [0, 3] → score ∈ [0, 1]).

## Implications for specint

- Feeds `docs/plan-2026-07-16.md` → Quality & scoring (H4) → the new
  `procedural_density` component gets a defensible normalization
  constant.
- Feeds Comparison discipline (`AGENTS.md` §Comparison-First): once we
  have parity fixtures we can add a *label-agreement* benchmark row
  ("does specint's step count on Wikibooks Chicken Alfredo agree with
  YouCook2's manual annotation for the same recipe?"). Filed for the
  next adversarial plan.
- Confirms the narrow choice of cooking as tractable — the ontology
  fits in a single file, the language is imperative English, and the
  gold benchmarks are public even when the media is not.
