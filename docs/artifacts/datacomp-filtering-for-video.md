# DataComp — Filtering recipes adapted to video

> Source: Gadre et al., "DataComp: In search of the next generation of
> multimodal datasets" (NeurIPS 2023, arXiv 2304.14108) and
> "Who's in and who's out? A case study of multimodal CLIP-filtering in
> DataComp" (arXiv 2405.08209).
> Notes captured: 2026-06-24 by Adversarial-Agent.

## TL;DR

DataComp builds **CommonPool** (12.8B image-text pairs from Common Crawl,
released as a CC-BY-4.0 *index* of URLs, not raw bytes) via a 4-step
pipeline:

1. **URL extraction + download** (img2dataset).
2. **NSFW filtering** (toxicity classifiers).
3. **Evaluation-set near-duplicate removal** (~3% of pool flagged on
   16.8B images).
4. **Face blurring.**

Then a *filtering track* lets researchers compete on selecting subsets
of CommonPool. CLIP-score filtering is the strong baseline.

## Why this matters for video

We are not building an image dataset. But the **4 steps generalise
cleanly to video**:

| DataComp (image)           | Our video-flywheel equivalent                                  |
|----------------------------|---------------------------------------------------------------|
| 1. URL extraction          | Common Crawl WAT/WARC `<video>` and `<source>` tag extraction |
| 2. NSFW filter             | per-frame NSFW classifier on a small sample of frames         |
| 3. Eval-set near-dup       | pHash blocklist + embedding match against held-out probes     |
| 4. Face blur               | face + PII (mail, plates, OCR) redaction on shipped frames    |

DataComp *ships an index*, not bytes. That is our default posture too
(`db_structured.md` §1). Their CC-BY-4.0 license is the same posture
we'd want for any released manifest.

## Concrete actions for our repo

1. **Step 3 today.** `components/eval_blocklist.py` (added today) is
   the first concrete piece. It loads pHashes from `data/eval_blocklist/`
   and rejects clips within a Hamming threshold.
2. **Step 4 next.** Plan a `components/redact/` module with two
   sub-components: `face_blur` (RetinaFace + Gaussian blur) and
   `ocr_redact` (PaddleOCR-driven text-region blur). Both are
   **off the critical path** until we actually ship frames.
3. **Step 2 next.** Borrow OpenNSFW2 or a similar permissively-licensed
   model. Apply only on the clip-keyframes (1 frame per scene), not
   per-frame.
4. **Cite the harms paper.** The "Who's in and who's out?" critique of
   CLIP-filtering applies to us: filter-by-CLIP-score *amplifies* English-
   language and Western-cuisine bias. Our cuisine-diversity audit (open
   question §7.3 of `docs/plan/2026-06-20.md`) is a direct response.

## Adversarial concerns

- **Cooking video is *much* sparser on Common Crawl than alt-text
  images on the web.** We will likely find ~10⁴–10⁵ candidate URLs, not
  10¹⁰. Don't blindly copy DataComp's quantitative thresholds.
- **CC-BY-4.0 for our *manifest* does not launder the underlying video
  bytes.** We must keep license_clean / license_unknown flags per row
  and never strip them in derived shards.
- **CLIP for filtering is itself trained on data of dubious license
  provenance.** Once we have V-JEPA-class embedders, we should prefer
  those for our retrieval filter (matches the V-JEPA 2 note adjacent to
  this one).

## Key references

- arXiv 2304.14108 (DataComp): §4 "CommonPool construction", Appendix F
  (near-dup details).
- arXiv 2405.08209 (Berman et al., 2024): demographic and license
  externalities of CLIP filtering.
- img2dataset: <https://github.com/rom1504/img2dataset> (BSD-3).
