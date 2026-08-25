# Dedup fingerprints — pipeline stages

Author: Coding-Agent · Date: 2026-08-25

We want to *never* count the same physical video twice in
`n_records`/`total_duration_s` aggregates, but we also want the earliest
possible collapse so we don't waste bytes downloading duplicates.

## Stages we plan

| Stage | When it runs | Fingerprint | Cost | Recall | Precision |
| ----- | ------------ | ----------- | ---- | ------ | --------- |
| **URL canonicalisation** | in-adapter, per record | `canonical_url()` | O(1) | Low  | Perfect |
| **Title shingles + Jaccard** | after per-source aggregation | 5-char shingles, threshold 0.85 | O(n²) per query batch | Medium | High |
| **Content hash of JSON payload** | not yet — but planned | SHA-256 of raw upstream body via `provenance.raw_sha256` | O(1) | Low | Perfect |
| **Perceptual video hash (pHash)** | only for records we download | e.g. `videohash` 64-bit dHash | O(seconds/video) | High | Medium |
| **MLT-Dedup (learned)** | offline batch, on the training corpus | KDD '26; learns a joint text/video embedding | Expensive | High | High |

The current codebase ships stages 1 and 2 only. Stage 3 is already
plumbed via `provenance.raw_sha256` (see `records.sha256_of_raw`).
Stage 4 and 5 land after we have downloaded corpora.

## What we buy from Tier 2 today

The unit tests in `tests/test_dedupe.py` show:

- `youtu.be/xyz` collapses onto `youtube.com/watch?v=xyz`.
- "Classic Garlic Butter Pasta" and "Classic garlic-butter pasta!"
  collapse across sources when Jaccard ≥ 0.7.
- Same-source records **never** merge (protects PeerTube's per-instance
  federation semantics).

## What we don't have yet

- **Cross-source title translation.** "Coq au vin" and "chicken in wine"
  are the same video; Tier 2 misses it. This is the primary motivator
  for MLT-Dedup.
- **Adversarial fixtures.** Our shipped fixtures don't include an
  intentional Wikimedia↔Internet Archive mirror pair — this is why the
  fixture harness reports `__deduped__ == __total__` today. Follow-up
  work: add mirror fixtures so the dedup gate is exercised end-to-end.

## References

- MLT-Dedup: [KDD '26 paper](https://kdd.org/) (learned dedup for large
  multimodal corpora).
- SVD benchmark (near-duplicate video retrieval), CVPR '11 — still the
  reference test set for pHash-style methods.
- `videohash` (Python) — good starting-point library for stage 4.
