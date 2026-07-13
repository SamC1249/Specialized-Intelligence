# Action100M — 100M action instances from 1.2M procedural videos (2026)

- **Source.** *Action100M: A Large-scale Video Action Dataset*, arXiv:2601.10592
  (Jan 2026). Uses ~1.2M instructional videos to produce ~147M
  temporally-localized action segments; pretrains VL-JEPA on the result.
- **Claim we care about.** LLM-aggregated *brief actions* over hierarchical
  temporal evidence Pareto-dominates flat pseudo-labeling for step-centric
  and motion-focused downstream tasks. Semantic resampling matters — long-
  tail redundancy hurts sample efficiency.

## Method summary

- Two-pass labeling: (1) short-window pseudo-labels from an off-the-shelf
  action recognizer; (2) LLM aggregates those into hierarchical action
  segments (verb+object+manner) with cross-window consistency checks.
- Semantic resampling: cluster embeddings of the aggregated segments and
  downsample the head to lift the tail.
- Pretrain VL-JEPA in three curriculum stages: query-free base, brief-
  action supervised, then long-horizon multi-step.

## What it changes for us

1. **Step-density is a first-class quality signal.** Our current
   `has_steps` binary + `text_density` conflate "there is any recipe text"
   with "there is procedural supervision". Add a follow-up metric
   `n_steps` (integer count of `recipe_steps`) and expose it in
   `BenchmarkResult` in a *backwards-compatible* way: keep the current
   fields, add new ones with defaults.
2. **De-duplicate before scoring.** Semantic resampling is exactly what our
   long-tail cooking crawl will need. Ship stub `specint.quality.dedup`
   that at minimum deduplicates by `(source, source_native_id)` and by
   normalized `title`; leave embedding-based dedup as a TODO gated on
   `sentence-transformers` (heavy dep, keep optional).
3. **Cross-source deduplication is expected.** WDC + Wikimedia frequently
   reference the same media. The comparison harness must treat cross-
   source duplicates as a red flag (yield inflation).

## Risks / disagreements

- "1.2M procedural videos" upstream in this paper is HowTo100M-derived and
  therefore *not* license-clean under our rules. We should replicate their
  ideas (LLM aggregation, semantic resampling) on our *own* legally-sourced
  corpus rather than take their pipeline as-is.
- LLM aggregation introduces a hallucination surface for step boundaries.
  Any implementation must include a step-boundary consistency check
  against source-provided timestamps (e.g. Common Crawl `Recipe`
  `recipeInstructions` order).
