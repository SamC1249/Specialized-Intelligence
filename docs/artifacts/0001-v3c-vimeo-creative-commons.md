# 0001 — V3C: Vimeo Creative Commons Collection

- Source: Rossetto, Schuldt, Awad, Butt. *V3C – a Research Video
  Collection.* arXiv:1810.04401. Used at TRECVid 2019–present.
- Reviewed: 2026-08-26 by Adversarial-Agent.

## What is it?

V3C is a research-only redistribution of **~28,450 Vimeo videos (~3,800
hours)** filtered to Creative Commons licenses, split into V3C1 (1,000
h), V3C2 (1,300 h), V3C3 (1,500 h). Each partition ships with per-video
JSON metadata (title, keywords, description), *pre-computed shot
boundary lists*, and both full-resolution and low-resolution keyframes.
As of TRECVid 2025 it is still the largest openly-published CC video
corpus with clean provenance.

## Why does it matter?

- It is a **defensible upper-bound baseline** on "how many hours of
  legally-permissive video can one platform yield." Our current
  Wikimedia/Archive/PeerTube estimates should be compared against V3C's
  yield-per-crawl-day.
- Shot boundaries + keyframes are exactly the pre-download quality
  filters we plan to add: they let us score procedural density
  (frequency of cuts) and scene diversity without ever fetching frames.
- V3C's methodology is a clean template for our own "compile once,
  redistribute metadata + derived features" model that stays inside
  fair use.

## Implementation ideas for `specint`

1. **Do not re-host V3C.** Instead, treat V3C's metadata JSON as a
   *third-party manifest* we can ingest through a new
   `sources/v3c_manifest.py` adapter that reads the checked-in
   `tests/fixtures/v3c/*.json` in unit tests and, in integration mode,
   reads the officially-published manifest URL for participants who
   have signed the V3C data agreement. Records land as
   `source="v3c"` with `License.CC_BY` (or the specific CC variant).
2. **Steal the shot-cut density feature.** Add a
   `quality/procedural.py:score_shot_density(record)` that reads
   `keywords` for a `shots=<n>` hint we synthesize from V3C's shot
   list. Later, extend to any source that supplies pre-computed shot
   segmentation (PeerTube's `state.transcodingJobs` sometimes exposes
   keyframe timings; Wikimedia can be derived from ffprobe on the
   media URL).
3. **Cross-source overlap audit.** V3C is a snapshot of Vimeo circa
   2019; many videos have since been re-uploaded to PeerTube or the
   Internet Archive. Use V3C's `contentUrl`, title, and duration as a
   deduplication anchor — a new `quality/dedup.py:cross_source_overlap`
   should compute (source_a, source_b, jaccard_by_title_shingles,
   duration_delta_s) so we quantify the double-counting risk.

## Benchmark row that would prove it

Add a `--include v3c_manifest` mode to `python -m specint compare` that
emits:

```
source          n_records  total_duration_s  mean_quality
v3c_manifest    28450      13_680_000        <computed>
```

And a paired `dedup_report` row:

```
pair                       overlap   jaccard   mean_duration_delta_s
v3c_manifest×peertube      <int>     <float>   <float>
```

If Jaccard > 0.05 we know the naive union of sources overstates unique
yield and we must add cross-source dedup **before** claiming yield
numbers publicly.

## Constraints & risks

- V3C requires a signed data-use agreement to download the raw videos.
  We must never download the videos themselves in CI; only the
  publicly-listed metadata manifests are fair game.
- Vimeo has occasionally changed CC licenses on individual videos
  post-upload. The V3C manifest's `license` field may drift from the
  current live license — we must re-verify at ingest time and default
  to `License.UNKNOWN` on any mismatch.
