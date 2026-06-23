# Strategy comparison framework

> Authored by Coding-Agent on 2026-06-23 to answer the standing question:
> *how do we know which curation strategy is better?*

## The question

For any internet-scale, license-clean video corpus, there is no single
"best" ranker — the right answer depends on whether downstream training
cares more about license-cleanliness, motion content, procedural density,
or simple bytes. The temptation is to ship one ranker, eyeball it on a
sample, and call it done. That is the *one-off moment* the AGENTS.md
contract explicitly rejects.

This repo's answer is to ship multiple rankers and *compare them
systematically every CI run*. The strategy harness
(`src/specint/compare/strategies.py`) implements that idea.

## The rankers we compare today

| Strategy | What it optimises | Why we keep it |
|---|---|---|
| `quality_metadata` | metadata-only quality (license tier × duration × resolution × text density × steps) | Baseline: cheap, runs without any video features. |
| `wm_utility` | world-model utility proxy (motion + steps + resolution + duration sweet spot − static-montage) | Closest to the documented Summer-22B / DreamDojo recipe; expected to disagree with `quality_metadata` on plated-food montages. |
| `license_confidence` | confidence in [0, 1] that the license tag is *actually* redistributable | Useful as a tie-breaker; pure-license sort is too coarse. |
| `license_then_wm` | filter to redistributable, then WM-utility | The realistic curator-facing rule; the headline ranker. |
| `random_baseline` | uniformly random subset, seeded | Negative control; if no strategy dominates random, the others have no signal. |

## What the harness emits

`compare_strategies(records, k, seed)` returns a list of
`StrategyResult`s, one per strategy, each with:

- `selected_ids` (sorted, so byte-identical across runs)
- `mean_quality`, `mean_wm_utility`, `mean_license_confidence`
- `license_clean_ratio`
- `unique_authors`
- `total_duration_s`

`strategy_overlap_matrix(results)` returns the pairwise Jaccard overlap of
the `selected_ids` sets. The matrix is symmetric and the diagonal is 1.

The CLI wrapper (`python -m specint strategies --top-k K --output PATH`)
runs the harness on the checked-in fixture corpus and writes the JSON
payload — a CI-reviewable artifact you can diff across PRs.

## How to read a strategy run

1. **If `random_baseline` matches the leaders on `mean_wm_utility`,**
   the candidate pool is too small / too homogeneous; the strategy
   choice does not matter and the difference is noise.
2. **If `license_then_wm` and `wm_utility` overlap >0.9 in Jaccard,**
   the license gate is not changing the top set — either the pool is
   already clean or the license tag is uninformative.
3. **If `quality_metadata` and `wm_utility` overlap <0.3,** they're
   measuring different things. That's our signal to look at *which*
   records each picks and update the WM-utility weights or the metadata
   quality scorer.
4. **`license_confidence` should never be the only ranker.** It's a
   guardrail, not a curator.

## What this framework does NOT yet do

- No ground-truth ranker. Until we have a held-out, license-clean
  evaluation set (the open question recorded in
  `docs/plan/2026-06-23.md`), the matrix is *all versus all*, not
  *all versus truth*.
- No learned filter. The `wm_utility` weights are an explicit opinion.
  Once we run a small training-loop ablation (Adversarial-Agent §7.2),
  we can drop a learned scorer in behind the same interface.
- No multilingual cuisine vocabulary. The audit currently lumps non-
  English titles into `other` / `unknown`; this is *visible in the
  CI artifact*, which is the entire point.
