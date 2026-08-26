# 0004 — MLT-Dedup, VidDup, and forge/dedup: near-duplicate video removal

- Sources:
  - Wang et al. *MLT-Dedup: Efficient Large-Scale Online Video
    Deduplication via Multi-Level Representations and Spatial-Temporal
    Matching.* KDD 2026, arXiv:2606.12215.
  - `Pengfei-Kou/viddup` — production-quality 3-layer video dedup
    (xxHash3 → duration prefilter → pHash on 10 sampled frames).
  - `arpitg1304/forge/dedup` — Tier 0 numpy-only per-episode pHash
    signature (pHash / dHash / aHash) with union-find clustering.
- Reviewed: 2026-08-26 by Adversarial-Agent.

## What is it?

Three complementary techniques for finding near-duplicate videos at
scale:

- **L1 exact-copy hash** (xxHash3-128 over the file bytes) — catches
  byte-identical copies for free.
- **L2 metadata prefilter** — group by duration ±5 %, source-declared
  codec, and (for our case) declared resolution buckets. Drops the
  O(N²) pair count to O(N·k) with k ≪ N.
- **L3 perceptual sequence hash** — 8–16 keyframes per video, pHash
  each, compare by *median* Hamming distance (robust to title cards,
  black frames, cross-fades). Then union-find clustering to collapse
  transitive duplicates.

MLT-Dedup adds a *spatial–temporal matching* stage that scores partial
temporal overlap, which matters when the "duplicate" is a shortened
re-upload (a 90-second highlight cut from a 15-minute video).

## Why it matters

Our current pipeline treats every source's records as independent. In
practice:

- Wikimedia Commons re-hosts many Internet Archive videos.
- Multiple PeerTube instances mirror the same channel.
- A Common Crawl recipe page often embeds a video that also has a
  Commons record.

If we naively add these hours together we will overstate yield **and**
train on the same footage repeated 3–5×, which is exactly the failure
mode world-modeling papers keep flagging as the largest silent quality
issue in web data.

We must add cross-source deduplication *before* claiming any hour
counts, and the cheapest, most legally-safe version does not require
downloading any media.

## Implementation ideas for `specint`

1. **`quality/dedup.py`** — pure functions, no media I/O:
   - `title_shingles(record, k=3) -> set[str]` — normalized k-shingle
     set of the lowercased title.
   - `signature(record) -> tuple[str, float | None, str]` — a
     `(host_of_source_url, duration_bucket_s, sha1_of_title_shingles)`
     tuple that already collapses ~80 % of the trivial cases.
   - `pair_score(a, b) -> float` — weighted combination of title
     Jaccard, duration delta, and author-string equality.
   - `cluster(records, threshold) -> list[list[VideoRecord]]` —
     union-find with early exit on signature equality.

2. **`compare` harness fields.** Add `n_after_dedup`,
   `duplicate_clusters`, and `dupe_rate` to `BenchmarkResult`. To
   preserve backwards compatibility, these are optional with default
   `0` / `None`, and the CI baseline check compares only fields present
   in the older baseline.

3. **Cross-source dedup as a first-class subcommand.**
   `python -m specint dedup --input reports/compare-*.json` reads the
   scored records, clusters, and emits `reports/dedup-YYYY-MM-DD.json`
   with per-cluster provenance (which sources agreed on this video).
   Every cluster gets a stable `cluster_id = sha1(sorted urls)` so
   subsequent runs are diffable.

4. **Adversarial test.** Add
   `tests/test_dedup.py::test_planted_duplicate` that constructs two
   `VideoRecord`s with different `source` but identical title +
   duration and asserts they cluster. Also a
   `test_no_false_positive_on_common_terms` that plants two records
   whose titles both start with "Chicken curry" but have completely
   different durations, and asserts they *do not* cluster.

## Benchmark row that would prove it

The right way to prove this is worth doing is to measure how much of
our declared yield is fake:

```
metric                     baseline_2026-06-20    post-dedup   Δ
n_records (fixture union)   8                     ?            ?
n_after_dedup               —                     ?            ?
total_duration_s            3021.4                ?            ?
```

If Δ ≥ 5 % on the fixture set (which contains no intentional
duplicates), our dedup is over-aggressive and we tighten
`threshold`. If Δ = 0, we need to plant test duplicates that
production would actually see (mirrors, re-encodes) and re-run.

## Constraints & risks

- Metadata-only dedup will **never** catch a re-uploaded video with a
  changed title and cropped duration. That's fine for stage 1; the
  full frame-hash dedup (VidDup L3, MLT-Dedup) belongs in a later PR
  where we've earned the right to download frames.
- False positives are worse than false negatives here: dropping a
  legitimate unique record is silent, silently wrong. Bias thresholds
  toward keeping duplicates and let the frame-hash stage arbitrate.
- All dedup work must remain a *pure function of already-collected
  metadata* to keep unit tests offline and CI reproducible.
