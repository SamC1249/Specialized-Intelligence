# DenseStep2M — training-free dense step annotation (arXiv 2604.26565)

- **Citation:** *DenseStep2M: A Scalable, Training-Free Pipeline for
  Dense Instructional Video Annotation.* arXiv 2604.26565 (2026).
- **Permalink:** <https://doi.org/10.48550/arxiv.2604.26565>

## One-paragraph summary

DenseStep2M is a *no-training* pipeline that turns noisy long-form
instructional video into densely annotated procedural training data.
Steps: (1) shot segmentation into visually coherent clips, (2)
filter segments with poor visual-text alignment, (3) joint reasoning
over frames + transcripts by Qwen2.5-VL-72B and DeepSeek-R1-671B to
produce structured, temporally-grounded step lists. Applied over ~99 K
HowTo100M videos this yields 2 M fine-grained steps, average 19
timestamped steps per video, 10.4 words per step. 59.1 % of the corpus
is "Food and Entertaining" — cooking dominates HowTo100M, which
is exactly our target vertical. Fine-tuning VLMs on DenseStep2M
significantly improves dense captioning, procedural grounding, and
cross-modal retrieval.

## Transferable to `specint`

- **Annotation-emission adapter.** Add a *post-collection* module
  `src/specint/annotate/densestep.py` that, given a `VideoRecord` with a
  reachable `media_url` **and** a redistributable license, emits an
  `ExecutableAnnotation` list. This keeps the network-free unit tests
  intact — we only run the VLM when a caller explicitly opts in.
- **Shot boundary heuristic in metadata.** Even without VLM inference
  we can approximate shot count from cadence hints in
  `description`/`recipe_steps` and treat *no shot text at all* as a
  quality penalty (add `_score_shot_hint` to `quality/metrics.py`).
- **Comparison metric.** Introduce `steps_per_minute` derived from
  `len(recipe_steps) / (duration_s / 60)` as a new column on
  `BenchmarkResult`. It is the closest metadata-only proxy for
  DenseStep2M's *dense procedural annotation density*.
- **Copy the visual-textual-alignment filter *idea***: when we do have a
  transcript and a title, penalise records whose title vocabulary has
  low Jaccard overlap with the transcript's top-k content words. This
  filter is cheap and offline-testable.

## NOT transferable

- The paper *uses* HowTo100M videos, which are indexed YouTube URLs
  under standard YouTube licence — **not** redistributable. We do not
  copy the HowTo100M IDs; we would build the equivalent only from
  CC-BY / CC-BY-SA / PD sources.
- The VLM models used (Qwen2.5-VL-72B, DeepSeek-R1-671B) are large;
  we won't run them in CI. Any adapter must be lazy and gated behind
  `SPECINT_RUN_ANNOTATION=1`, mirroring our `SPECINT_RUN_INTEGRATION`
  discipline.

## Adversarial notes

1. If DenseStep2M's *automated* labels rival human labels on
   `DenseCaption100`, then the bottleneck in our pipeline is no longer
   annotation — it is *legally-clean raw video*. That confirms our
   collection-first strategy.
2. 59.1 % of HowTo100M is food. If we can convert our current
   licence-clean corpus into a HowTo100M-shaped index (URL + title +
   transcript + shot count), we have a clean-room training-data
   substitute for the food vertical.
