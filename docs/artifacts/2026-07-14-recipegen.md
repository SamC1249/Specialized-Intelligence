# RecipeGen — 2026 step-aligned recipe benchmark

- **Paper**: RecipeGen: A Step-Aligned Multimodal Benchmark for
  Real-World Recipe Generation. arXiv:2506.06733 (v3, 2026).
- **Dataset**: Hugging Face `RUOXUAN123/RecipeGen`.
- **Declared license**: **CC BY-NC 4.0** — non-commercial only.
- **Scale**: 26,453 recipes, 196,724 step-aligned images, 4,491 cooking
  videos.
- **USE (per this repo's constraints)**: **reference-only**. We may
  compare our own harvested corpus against RecipeGen's distribution
  (durations, step counts, ingredient coverage) as a *benchmark*, but
  the records themselves must not enter any redistributable training
  corpus we ship. AGENTS.md forbids NC.

## Why it matters

RecipeGen is the first large-scale open benchmark that pairs (recipe
text → step images → step video keyframes). It confirms the industry
hypothesis that *step-alignment* is the axis frontier models are being
evaluated on — not raw hours-of-video. Datasets that supply steps at
scale (even at ~4.5K videos) are being used as gold.

## Concrete hooks into this repo

1. **License classifier must reject BY-NC unambiguously.** Add
   fixtures/adversarial license strings ("Attribution-NonCommercial
   4.0 International", "CC BY-NC-SA 4.0", "CC BY NC 4.0" with
   spaces/unicode) to `tests/test_license_classifier_edges.py`. Expected
   mapping: `License.RESTRICTED`. Any regression here would let RecipeGen-
   style records leak into a "clean" corpus.
2. **New record kind: `USE: reference-only`.** Propose a
   `record_class: Literal["train", "reference", "url_only"]` field on
   `VideoRecord` in a follow-up. `reference` = counted in benchmark
   stats but never emitted with a `media_url`.
3. **New comparison axis: step density.** RecipeGen normalizes step
   count per video; our `quality.metrics._score_has_steps` is binary.
   Upgrade to `step_density = n_steps / max(1, duration_min)` and put
   it in `BenchmarkResult` as a new column (guarded by a schema-version
   bump — do not break existing `reports/*.json` consumers).

## Legal note

CC BY-NC 4.0 is *not* redistributable under our contract. Even
metadata excerpts should carry the license label so downstream code
cannot accidentally promote them. If a Coding-Agent PR ever adds a
RecipeGen adapter, the reviewer checklist must verify that every
emitted record has `license = License.RESTRICTED` and `media_url = None`.
