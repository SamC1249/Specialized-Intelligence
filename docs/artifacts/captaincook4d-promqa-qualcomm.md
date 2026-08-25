# CaptainCook4D → ProMQA → Qualcomm Interactive Cooking

- **CaptainCook4D:** Peddi et al., 2023. Egocentric multi-modal cooking
  recordings with step-level annotations *including intentional user
  mistakes*.
- **ProMQA (NAACL 2025):** *Question Answering Dataset for Multimodal
  Procedural Activity Understanding*.
  <https://aclanthology.org/2025.naacl-long.579.pdf>
  Builds 401 multimodal QA pairs on top of CaptainCook4D cooking
  recordings.
- **Qualcomm Interactive Cooking (NeurIPS 2025):** *Can Multi-Modal
  LLMs Provide Live Step-by-Step Task Guidance?* Extends
  CaptainCook4D with timed instructions and mistake feedback.
  Videos are Apache-2.0 licensed via CaptainCook4D.

## What they tell us

Three consecutive top-venue benchmarks in 12 months all reduce to
*"understand a cooking video step by step, in the presence of user
mistakes"*. This is the exact downstream capability our world-model
data is meant to support. If our corpus ranking metric does not
correlate with usefulness for these benchmarks, our quality scoring
is measuring the wrong thing.

## Why it matters for Specialized-Intelligence

- **Justifies the cooking narrow-target choice.** The literature is
  actively converging on procedural cooking as the canonical
  long-horizon benchmark for multimodal LLMs / world models.
- **Confirms the "mistake / recovery" axis is under-served.**
  CaptainCook4D's differentiator is intentional errors. Our metadata
  scorer has no signal for this; a keyword heuristic
  (`"how to fix"`, `"common mistakes"`, `"my bread failed"`) could
  boost recall of mistake-containing videos in cooking-tutorial
  corpora.
- **Gives us a downstream metric.** We can, without doing any model
  training ourselves, evaluate our ranked-corpus quality by asking a
  frozen VLM to answer ProMQA-style questions on top-K vs. bottom-K
  of our own ranking. Higher accuracy on top-K → our metadata score
  is predictive of downstream usefulness.

## Concrete implementation ideas

- `src/specint/quality/procedural.py`: new metadata component
  `has_error_narrative` scoring keyword hits like
  `{"mistake", "failure", "troubleshoot", "went wrong", "how to fix",
    "common errors"}` (extend with translations for W3-follow-up
  multilingual work).
- Add a "mistake-density" fixture — a synthetic record whose title
  and description contain error-narrative keywords — and update the
  regression baseline once the component ships.
- Add `docs/artifacts/downstream-eval-recipe.md` (future) describing
  the exact frozen-VLM protocol for the top-K vs. bottom-K
  comparison. Keep it out of the CI runtime path — this is a
  weekly-scale evaluation, not per-commit.
