# Detecting Near-Duplicates for Web Crawling (Manku, Jain, Sarma — WWW 2007)

- Paper: https://research.google/pubs/detecting-near-duplicates-for-web-crawling/
- Foundation: Charikar, "Similarity estimation techniques from rounding
  algorithms" (STOC 2002).

## Claim

Charikar's SimHash — a random-hyperplane locality-sensitive hash —
maps a high-dimensional bag-of-features vector to a compact 64-bit
fingerprint such that Hamming distance approximates cosine similarity.
Manku et al. show this works at 8 billion pages: with 64-bit
fingerprints and Hamming-distance threshold *k = 3*, they get
high-precision near-duplicate detection. They also give a batch and
online algorithm that finds all fingerprints within Hamming distance
k of a query in time much better than linear scan (by permuting bits
into blocks and querying multiple sorted tables).

## Evidence

- Empirical: on a real 8B-page repository, k=3 catches boilerplate
  reuse, template mirrors, and light rewrites. False-positive rate is
  low enough for a crawl scheduler to use directly.
- Complexity: index of *m* fingerprints answers a k-bit-difference
  query in expected `O(m^(k/64))` after preprocessing, orders of
  magnitude below the brute-force `O(m)`.
- Alternative: **MinHash** (Broder 1997) estimates *Jaccard* similarity
  over sets. Cheaper for set-based features (n-grams), used in
  Wu/Hauptmann/Ngo 2009 for video near-duplicate detection.

## Steal

1. **64-bit SimHash on `title|description|host|duration_bucket`.** Ship
   a pure-Python `simhash(str) -> int` in
   `src/specint/quality/dedup.py`. No external deps — token-shingle,
   hash each shingle with SipHash-2-4 or md5-int, weighted vote each
   bit, sign to 0/1. Threshold at k=3 by default.
2. **Per-source *and* cross-source dedup.** Same recipe re-uploaded to
   multiple PeerTube instances collides on `title|description` but not
   on `host` — we deliberately shingle host as a *weak* feature so
   near-duplicates across hosts still collapse, while genuinely
   different videos with the same title on the same host stay
   separate.
3. **Report unique-record counts alongside raw counts.** Adds
   `n_unique_records` and `mean_quality_unique` to `BenchmarkResult`
   (append-only extension per plan).

## Implications for specint

- Directly enables `docs/plan-2026-07-16.md` → Dedup (H3) deliverables:
  `src/specint/quality/dedup.py` + BenchmarkResult extension.
- Keeps the pipeline offline-testable: dedup is a pure function of
  metadata strings; the fixture already contains two near-duplicate
  Blender PeerTube records we can collapse.
- Warning: **do not** implement k-bit-difference index today — a linear
  scan over the ≤10k records we hold at this stage is faster to write
  and correct, and the index only pays for itself past ~10⁵. File it
  as a follow-up in the next adversarial plan.
