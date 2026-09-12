# Video Deduplication at Scale

**Citations.**

- Kollias et al., "Detecting Duplicate Videos Via Perceptual Hashing",
  IEEE 2025 (DOI:10.1109/ieeeconf67917.2025.11443714) — 64-bit DCT hash
  baseline.
- MLT-Dedup, arXiv:2606.12215 — three-stage pipeline (multi-level
  encoder → HNSW retrieval → DiF-SiM fine-grained matching); reports
  91% online repetition removal at 90% precision.
- Hao et al., "Fast Distributed Video Deduplication via Locality-
  Sensitive Hashing with Similarity Ranking", J. Image & Video
  Processing 2019
  (<https://link.springer.com/article/10.1186/s13640-019-0442-7>).
- SQLite Hamming-distance extensions:
  <https://github.com/droe/sqlite-hexhammdist>,
  <https://notnotp.com/notes/hamming-distance-for-hybrid-search-in-sqlite/>.

## One-line summary

The current best practice is a three-stage cascade: cheap fingerprints
(perceptual hash, LSH bands, byte hash) → approximate nearest neighbour
retrieval (HNSW / LSH tables) → fine-grained spatial-temporal
verification. Every serious pipeline (SolarWM, Reka, MLT-Dedup) implements
this in some form.

## Why this matters for us

Even at the metadata-only tier we know we double-count:

- PeerTube federation mirrors the same video across instances (same
  `uuid`, different host).
- Internet Archive frequently re-hosts Wikimedia Commons videos with a
  slightly different title.
- Common Crawl surfaces the same recipe on multiple mirrors and syndication
  partners.

Without dedup, our `mean_quality` is systematically over-optimistic (a
duplicated high-quality record contributes twice) and our
`total_duration_s` is inflated. This is the single lever most likely to
change source rankings.

## Staged plan (metadata → embeddings)

**Phase 1 (this iteration): metadata-only near-dup.**

- Normalize URL (strip scheme, trailing slash, tracking params, common
  syndication prefixes; keep host + path).
- Tokenize title into lowercase alphanumeric words; discard stopwords
  from a tiny checked-in list.
- Compute Jaccard similarity on title-token sets.
- Bucketize `duration_s` into 15-second bins; two records are candidate
  duplicates if buckets are equal or differ by ≤ 1.
- Two records are *near-duplicates* if `title_jaccard ≥ 0.85` AND
  `duration_bucket_diff ≤ 1`, OR normalized URL matches exactly.
- Group records via union-find; report `n_unique / n_records` per
  source and aggregate.

**Phase 2 (next quarter): phash on cover / thumbnail images.**

Cheap CPU stage. Downloads only the thumbnail (bytes), not the video.
Encode with DCT-64 following the 2025 IEEE baseline. Store the 64-bit
hash on `VideoRecord.thumbnail_phash: int | None`. SQLite hexhammdist
lets us query "records within Hamming ≤ 8" without an external DB.

**Phase 3 (later): clip-level embedding + HNSW.**

Follow MLT-Dedup: encode short clip windows with a lightweight video
encoder, index with HNSW, and run DiF-SiM-style overlap verification.
This requires GPUs and stays out of CI.

## What to steal

- **Rejection-with-reason record** for dropped duplicates — see
  `2026-09-12-solarwm.md`.
- **Union-find grouping over a similarity graph** rather than pairwise
  keep-first; deterministic ordering by canonical URL breaks ties.
- **SQLite Hamming for the phash layer** to keep infra dependencies
  at zero. Only reach for pgvector / Milvus at Phase 3.

## What to not steal (yet)

- Full CLIP-style embedding dedup — needs GPUs; violates our "CI must
  pass without network / GPU" rule.
- Reciprocal-rank-fusion of BM25 + Hamming — cute for search, overkill
  for dedup.

## Follow-ups filed

- Ship Phase 1 today: `src/specint/quality/dedup.py` + CLI + report.
- Add `thumbnail_url` and `thumbnail_phash` optional fields to
  `VideoRecord` in a future schema PR (backwards compatible).
