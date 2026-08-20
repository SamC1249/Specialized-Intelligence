# MLT-Dedup — multi-level embeddings + spatial-temporal matching for online video dedup

- Paper: *MLT-Dedup: Efficient Large-Scale Online Video Deduplication
  via Multi-Level Representations and Spatial-Temporal Matching*
  (KDD '26). https://arxiv.org/html/2606.12215
- Accessed: 2026-08-20.

## What it does

Two-tier online dedup deployed on a large short-video platform:

1. **ML-VE** ("Multi-Level Video Encoder") produces two embeddings per
   video:
   - a **clip-level** compact vector for scalable ANN retrieval, and
   - a **frame-level** dense sequence for fine-grained copy
     localization.
2. **DiF-SiM** ("Differential Feature-enhanced Similarity Module") does
   the verification step on recalled candidates. It integrates
   differential features to capture temporal dynamics, pretrained
   self-supervised.

Deployed at web scale, catches near-duplicates from clipping,
watermark insertion, transcoding, and reflection/rotation attacks.

## Why it matters for us

Ingest surfaces (Wikimedia, Archive.org, PeerTube, Common Crawl) are
**heavily contaminated with re-uploads** — the same cooking demo may
appear as an mp4 on Archive, a WebM on Wikimedia, an embed on a recipe
blog crawled through Common Crawl, and a PeerTube copy. If we do not
dedup, every downstream metric (yield, mean quality, unique authors)
is inflated.

## Ideas we should steal

1. **Two-tier retrieval + verification** is the right architecture:
   cheap recall, expensive verify. Landing site:
   `src/specint/dedup/` with a `Recall` abstract class (MinHash today,
   embeddings later) and a `Verify` abstract class (URL + duration
   agreement today, frame-embedding cosine later).
2. **Differential features** on temporal windows — even a
   metadata-only version is useful: `abs(duration_a - duration_b) /
   max(duration_a, duration_b)` as a coarse "same-video" prior.
   Landing site: `dedup/verify.py::duration_agreement`.
3. **Watermark/transcode robustness**: even our metadata dedup should
   be robust to differing MIME types (`.webm` vs `.mp4`) and
   resolution ladders — do not use MIME/resolution as identifiers.

## Ideas we should refuse

- Training a proprietary embedding model. We would need a
  license-clean training set, which is precisely what we are trying to
  collect. Bootstrapping this end is a chicken-and-egg.
- Copying weights of any of their released checkpoints (author license
  unclear at time of access).

## Follow-ups for `plan-YYYY-MM-DD.md`

- Ship a MinHash-based near-dup detector (metadata only) *today*, with
  a `dedup_bench.py` that reports fraction-removed per source across
  fixtures. Even at fixture scale we expect ≥1 collapse
  (Wikimedia knife-skills demo vs. Archive.org knife-skills demo, if
  fixtures allow it).
- Extend the harness to report `n_records_after_dedup` and to
  attribute a duplicate to its *canonical* source (highest license
  tier > highest resolution > earliest publish date).
