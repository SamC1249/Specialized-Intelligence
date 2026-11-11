# Artifact — Procedural / step-boundary segmentation (2022–2025 state of the art)

**Access date:** 2026-11-11.

## Papers surveyed

| Paper | Venue | URL | What it does |
| --- | --- | --- | --- |
| Zhu et al., *Cluster-Refined Optimal Transport for Unsupervised Action Segmentation* | ICASSP 2025 | https://doi.org/10.1109/icassp49660.2025.10887693 | Hierarchical clustering → optimal-transport refinement for frame→segment labels on long untrimmed videos. Tested on YouTube Instructions, Breakfast, 50Salads. |
| Spurio et al., *Hierarchical Vector Quantization for Unsupervised Action Segmentation (HVQ)* | 2024 | https://www.alphaxiv.org/abs/2412.17640 | Two stacked VQ modules → hierarchical sub-clusters that match the true segment-length distribution. Introduces a Jensen-Shannon-distance metric for unsupervised evaluation. |
| Li et al., *OTAS: Unsupervised Boundary Detection for Object-Centric Temporal Action Segmentation* | WACV 2024 | https://openaccess.thecvf.com/content/WACV2024/papers/Li_OTAS_Unsupervised_Boundary_Detection_for_Object-Centric_Temporal_Action_Segmentation_WACV_2024_paper.pdf | Object-centric local features yield better boundary F1; reported +41% F1 vs prior SotA; surprisingly outperforms some ground-truth-driven methods. |
| Nair et al., *A Closer Look at Temporal Ordering in the Evaluation of Procedure Segmentation and Summarization* | BMVC 2022 | https://pdf-files.bmvc2022.org/0669.pdf | Shows standard F1 overestimates segmentation quality because it ignores temporal order. Proposes an order-aware metric and an order-constrained matching loss. Evaluated on YouCook2 and Tasty. +~7% segmentation F1. |
| Khanna & Kundu, *FLICSNet: A Novel Framework for Cooking Action Segmentation from Video* | 2025 | https://doi.org/10.1145/3746264.3760478 | Cooking-specific action segmentation framework; useful as a target model to *benchmark our dataset on* once we have one. |

## Common threads

1. **Step boundaries are the single most predictive dense annotation
   for downstream world-modeling quality on cooking data.** All
   five papers treat boundary prediction (not caption quality, not
   object detection) as the primary metric.
2. **Unsupervised boundary methods work well when the data is
   procedural, poorly otherwise.** CROT and HVQ specifically assume
   non-overlapping ordered steps. This gives us a diagnostic: a
   corpus for which unsupervised segmentation methods *fail* is
   probably not procedural enough to be useful for world-model
   pretraining.
3. **Temporal order matters at eval time.** The BMVC'22 paper
   argues that if you don't enforce order, you overcount good
   segmentations. Any evaluation we run on cooking world models
   should use their order-aware metric, not vanilla F1.

## Why this matters for Specialized-Intelligence today

We are not ready to run frame-level segmentation — we have no video
bytes. But metadata already contains a *weak proxy* for procedural
density: the Common-Crawl Recipe JSON-LD blocks embed
`recipeInstructions` as an ordered list of `HowToStep` objects with
`text` and sometimes `image`/`video`. The number of steps, the
average step length, and the fraction of step text that is
imperative ("whisk", "sear", "fold") predict whether the underlying
video is procedural at all.

## Implementable takeaways for `Coding-Agent`

- Add `src/specint/quality/procedural.py`:
  - `procedural_density(record) -> (n_steps: int, avg_step_chars:
    float, imperative_verb_ratio: float)`.
  - `score_procedural(record) -> float in [0,1]`: logistic blend of
    the three.
- Vendor a small English imperative-verb list
  (`src/specint/quality/data/imperative_en.txt`, ~200 verbs) under
  CC0. Add a `# TODO: multilingual` comment so this is clearly
  flagged for H4.
- Add `procedural_score` as a column in `BenchmarkResult` (not a
  weighted component of `quality_score` initially — we want to track
  it separately before letting it move the primary score).
- Document in the plan that once we have real video bytes, the
  `procedural_score` *predictor* should be validated against actual
  CROT/HVQ-style boundary detections on the same videos. That
  validation is a future deliverable, not today's.
