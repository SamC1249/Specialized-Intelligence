# 2026-06-23 — Video curation pipelines (Cosmos, NeMo, DenseStep2M, HowToCaption)

Author: `Adversarial-Agent`

The state of the art for industrial-scale video curation in 2026 is
basically NVIDIA's stack (Cosmos Curator on top of NeMo Curator / Ray /
Xenna). We should not re-implement what they have already open-sourced;
we should *plug into* their stages and add the parts that are missing for
our specific play.

---

## 1. NVIDIA Cosmos Curator (2025-2026, Apache 2 code + NVIDIA Open Model)

Reference pipeline used to build the Cosmos World Foundation Models. Seven
stages, Ray-orchestrated, GPU-streaming:

1. **Shot-aware splitting** (scene-change OR fixed-stride fallback)
2. **Transcoding** (GPU-accelerated H.264 via nvenc/nvdec)
3. **Quality filtering** (motion, OCR text density, aesthetic, content-type
   classifier that rejects animation / static slideshows)
4. **VLM filter** (Qwen2.5-VL semantic validation)
5. **Captioning** (Qwen2.5-VL, multi-length: short / medium / long)
6. **Semantic deduplication** (embedding clustering, then pairwise cosine
   inside clusters; keep highest-resolution survivor)
7. **Structured sharding** (WebDataset, grouped by content / resolution /
   aspect ratio / temporal length)

Reported scale: ~100M clips (2-60s each) extracted from ~20M hours of
source video.

**Our use:** adopt stages 1, 2, 3, 6, 7 as-is. Wrap stages 4 and 5 with
our procedural-step variant (next section).

## 2. NVIDIA NeMo Curator (video)

Lower-level building blocks underneath Cosmos. Exposes `ClipWriterStage`,
embedding generators (`cosmos-embed1-224p`, `InternVideo2`), and a
modular `Pipeline` API. This is the one we actually `pip install`.

## 3. DenseStep2M (2026)

Training-free pipeline that converts noisy HowTo100M into 2M
**dense procedural step** annotations across 100k videos:

1. Shot segmentation.
2. ASR refinement (LLM rewriting + timestamp interpolation).
3. **Visual-textual alignment verification** with Qwen2.5-VL-7B — only
   videos whose aligned segments cover >75% of total length are retained.
4. LLM-generated structured steps (DeepSeek-R1).

Validated against a 100-video human-written benchmark (DenseCaption100).
Fine-tuning VLMs on DenseStep2M significantly improves dense captioning,
procedural grounding, and cross-modal retrieval.

**Our use:** this is our captioning stage. We adopt it almost verbatim,
with two changes:

- Replace HowTo100M source with our license-clean discovery set.
- Replace DeepSeek-R1 with a 2026 open-weights reasoner of our choice
  (likely Qwen3-Reasoning or DeepSeek-R2 — to be pinned in
  `db_structured.md`).

## 4. HowToCaption (ECCV 2024)

Older but complementary technique: prompt an LLM to summarise blocks of
ASR subtitles into structured captions, predict per-sentence timestamps,
then post-process the timestamps using a video-language model
(`sim(f(caption), g(video_clip))`) with a `±T` second offset search and a
similarity-threshold filter.

**Our use:** HowToCaption is the *fallback* when DenseStep2M's
Qwen2.5-VL alignment check rejects too many segments. We keep it as a
secondary captioner so we don't lose long videos that have good ASR but
bad shot structure.

---

## How our curation pipeline differs from Cosmos's

| Stage              | Cosmos                                      | Ours                                                                                       |
| ------------------ | ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Source             | unspecified 20M h corpus                    | **license-clean only**; per-source manifests; CC-BY/CC0/PD only.                            |
| Split              | scene-change or fixed stride                | same.                                                                                       |
| Filter             | motion, OCR, aesthetic, content-type        | same + **kitchen-content classifier** (Qwen2.5-VL one-shot: "is this a kitchen?").          |
| Caption            | short/medium/long Qwen2.5-VL                | DenseStep2M-style **procedural steps** + short caption, both with ASR-anchored timestamps.  |
| Annotate (new)     | n/a                                         | per-clip recipe grounding + object-state-before/after via Qwen2.5-VL prompted on key frames.|
| Dedup              | semantic embedding clustering               | same, plus **contamination check** against EPIC-K, HD-EPIC, YouCook2, OmniWorld.            |
| Shard              | WebDataset grouped by content/res/AR/length | same + per-shard `datacard.md` with license breakdown.                                      |

The two genuinely new stages are the **kitchen-content classifier** and
the **contamination check**.

---

## Sources

- Cosmos World Foundation Model paper: <https://arxiv.org/html/2501.03575v1>
- Cosmos Curator README: <https://github.com/NVIDIA/cosmos-curator>
- Cosmos reference video pipelines: <https://github.com/nvidia-cosmos/cosmos-curate/blob/main/docs/curator/REFERENCE_PIPELINES_VIDEO.md>
- Cosmos Cookbook overview: <https://nvidia-cosmos.github.io/cosmos-cookbook/core_concepts/data_curation/overview.html>
- Cosmos Cookbook core curation: <https://nvidia-cosmos.github.io/cosmos-cookbook/core_concepts/data_curation/core_curation.html>
- NeMo Curator video docs: <https://docs.nvidia.com/nemo/curator/v25.09/curate-video>
- NeMo Curator process-data: <https://docs.nvidia.com/nemo/curator/curate-video/process-data>
- DenseStep2M paper: <https://arxiv.org/html/2604.26565>
- DenseStep2M dataset: <https://huggingface.co/datasets/mingjige/DenseStep2M>
- HowToCaption (ar5iv): <https://ar5iv.labs.arxiv.org/html/2310.04900>
- HowToCaption (ECCV 2024 PDF): <https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/07249.pdf>
