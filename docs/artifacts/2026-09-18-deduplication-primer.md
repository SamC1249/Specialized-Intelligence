# Near-duplicate video detection primer — 2026-09-18

`Adversarial-Agent` note. We currently do **no** dedup: the same Big Buck
Bunny clip can appear on Wikimedia, PeerTube (framatube.org), and
Internet Archive, and count as three "unique" records that inflate every
per-source yield metric.

## Baseline (must ship first)

1. **URL canonicalisation.** Lowercase host, strip default port, sort
   query params, drop fragment, strip trailing slash. Yields the cheapest
   possible cross-source dedup key.
2. **Content-title fuzzy match.** After lowercasing and stripping
   punctuation, compare titles with `rapidfuzz.token_set_ratio ≥ 92`.
3. **Duration bucketing.** Two candidates with identical canonical URL
   base and duration within 1 s are almost certainly the same file.

That is enough to catch the Wikimedia ↔ Framatube ↔ Archive.org overlap.

## When we start ingesting frames

Once we have media downloaded (post-license-check), we should adopt a
perceptual-hash pipeline. Options:

| Algorithm  | Signature size | Robustness         | Notes                                      |
| ---------- | -------------- | ------------------ | ------------------------------------------ |
| pHash / PDQ | 64 or 256 bits | crop/watermark/reencoding | Meta's PDQ used in ThreatExchange; hamming compare |
| vPDQ       | ~N PDQ hashes/video | short-clip subset detection | Frame-level PDQ, overlap scoring |
| TMK+PDQF   | 256 KB per video | full-video match at 15 fps | Cosine + sine trig-weighted temporal kernel |
| videohash2 | 64 bits | full-video (1 fps collage) | Cheap Python, DCT + dominant colour        |

Pipeline sketch:

1. Sample keyframes at 1 fps (or IDR frames).
2. Compute PDQ per keyframe → per-video vPDQ signature.
3. LSH bucketing on the PDQ hash → candidate pairs within Hamming ≤ 16.
4. Rank candidates by fraction of matched keyframes and temporal order
   agreement (longest-common-subsequence over frame indices).
5. Keep the record with (a) the most permissive license and (b) the
   highest resolution; store the alternates as `duplicate_of` pointers.

Citations:

- Distributed LSH for video dedup: <https://link.springer.com/article/10.1186/s13640-019-0442-7>
- Facebook ThreatExchange (PDQ/vPDQ/TMK): <https://github.com/facebook/ThreatExchange>
- videohash2: <https://github.com/demmenie/videohash2>

## First deliverable: metadata-only dedup

For today's PR we do not need frame-level dedup. We do need:

- `specint.dedup.canonical.canonical_url(url) -> str`
- `specint.dedup.canonical.dedup(records: list[VideoRecord]) ->
  list[VideoRecord]` (stable, prefers more-permissive license, then
  higher `duration_s`, then higher `height`)
- benchmark harness reports `n_duplicates_removed` per pair (source_a,
  source_b) and reports the pairwise Jaccard of *canonical URL sets*.

That alone is defensible against critics who currently doubt that our
per-source yields are non-overlapping.
