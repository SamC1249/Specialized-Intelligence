# docs/artifacts/ — annotated research notes

Each file summarizes one paper, dataset, or system and calls out **the
concrete hook back into this repo** (which module changes, which
`BenchmarkResult` field it moves, which invariant it locks in).

Naming: `YYYY-MM-DD-slug.md`. Newest on top of the index below.

## Index

- 2026-07-14: `2026-07-14-recipegen.md` — CC-BY-NC benchmark; use as
  reference-only comparator, must be blocked from training corpora.
- 2026-07-14: `2026-07-14-densestep2m.md` — training-free step
  annotation pipeline; blueprint for our `quality/step_alignment.py`.
- 2026-07-14: `2026-07-14-recipe-rl.md` — verifier-cheaper-than-labeler
  asymmetry; motivates our `quality/verifier.py` roadmap.
- 2026-07-14: `2026-07-14-panda70m-filters.md` — six desirability
  categories + shot boundary detection; guides the "metadata-only
  proxy" filters we can compute without downloading video.
- 2026-07-14: `2026-07-14-wbench-worldprediction.md` — evaluation
  dimensions and horizon settings for world-model benchmarks; tells us
  what "quality" ultimately means downstream.

## Reading rules for future entries

1. State the paper's contribution in one paragraph.
2. Identify **which invariant, filter, or benchmark row it changes** in
   this repo. If the answer is "nothing", the entry should not exist —
   put it in a plan under "surveyed but not adopted".
3. Include the arXiv / DOI / URL and (if a dataset) the declared
   license. Datasets with non-redistributable licenses must be flagged
   `USE: reference-only`.
