# Perceptual video hashing for near-duplicate detection

## Citation

- akamhy et al. *videohash — Near Duplicate Video Detection.*
  <https://github.com/akamhy/videohash>. 64-bit wavelet-hash-of-collage
  fingerprint per video.
- Kumar et al. *Detecting Duplicate Videos Via Perceptual Hashing.*
  IEEE 2025, doi:10.1109/ieeeconf67917.2025.11443714. DCT-based 64-bit
  fingerprint; high-frequency uncropped variant dominates.
- Sohail et al. *Comparative Evaluation of Perceptual Hashing and Deep
  Embedding Methods for Robust and Efficient Image Deduplication.*
  Electronics 15(7):1493, 2026. Confirms trade-off: hashes are fast and
  reliable for exact/near-exact duplicates; CNN embeddings dominate
  under geometric transforms at ~100× the cost.

## One-paragraph summary

Perceptual video hashing produces a compact (usually 64-bit) fingerprint
that is *similarity-preserving under re-encoding, rescaling, watermarking,
and minor cropping*. Two videos are considered near-duplicates when the
Hamming distance between their hashes falls under a threshold (typically
6–12 bits for 64-bit hashes). At scale, pairwise Hamming becomes O(n²);
BK-trees and LSH bring this down to sublinear. The 2025 IEEE result
shows that a **high-frequency DCT** variant of the standard `pHash` gives
the best trade-off between false positives and recall on re-encoded
videos, and the 2026 Electronics study confirms that classical hashes
lose to CNN embeddings *only* under aggressive geometric transforms —
which are rare in the wild for user-uploaded video.

## What it changes for `specint`

- Immediately: motivates **H2 (metadata-only dedup)** in
  `docs/plan-2026-07-12.md` as a *baseline* that any future perceptual
  hash must beat by a documented margin on the same fixtures. If
  metadata alone catches 5% of duplicates, then a downstream perceptual
  hash only needs to explain its additional *marginal* recall to be
  worth the cost of downloading frames.
- Roadmap: after we have a media-fetch worker, add
  `quality/video_phash.py` computing a 64-bit fingerprint per record,
  storing it in `VideoRecord.provenance` (or a new sibling model), and
  indexing via a BK-tree in `quality/dedup.py`. Compare against the
  metadata baseline via the existing `compare` harness.
- Directly informs `BenchmarkResult` extension: we need
  `n_unique_after_dedup` *and* a `dedup_method` note, because the
  headline number changes materially depending on whether we deduped by
  metadata, by pHash, or by CNN embedding.
- Legal note: computing a perceptual hash of a copyrighted video is
  fine (we produce a derivative *representation*, not the media), but
  distributing the *hash index alongside copyrighted URLs* raises
  contributory-infringement questions. We should only publish hash
  indices for records whose license is in
  `License.is_redistributable`.

## Attack surface

- **Adversarial re-encodes.** Any determined uploader can defeat a
  64-bit wavelet hash with a large enough affine transform. This is not
  a threat for our dedup use case (we're trying to *find* duplicates,
  not stop bad actors from evading us), but a Reviewer should confirm
  we do not build a downstream *content-authenticity* claim on top of
  the same hash.
- **Cross-source aliasing.** Wikimedia's `File:Foo.webm` and Internet
  Archive's `identifier=foo` can be identical bytes with different
  metadata. A metadata-only dedup misses them; a pHash catches them.
  This is precisely the gap the plan expects future perceptual-hash
  work to close.
- **CPU cost.** `videohash` extracts one frame per second → an 8k-hour
  corpus (YFCC100M scale) is 28.8M frames of hashing work. Fine on a
  single beefy box (~ tens of hours), but we should budget for it before
  turning it on in CI. In particular, **do not** call `videohash` on
  the pytest offline path — it would either need real video files
  (blocked by our fixture-only rule) or a mock so weak that the test
  loses value.
