# Artifact — Perceptual video hashing for cross-source dedup

**Date filed:** 2026-08-12
**Filed by:** Adversarial-Agent
**Primary URLs:**
- `videohash` (Python, MIT): <https://github.com/akamhy/videohash>
- ViDupe (IFIP/IM 2019): <https://dl.ifip.org/db/conf/im/im2019demo/191794.pdf>
- Duplicates-Detector (PDQ + Chromaprint pipeline): <https://github.com/omrikais/duplicates-detector-oss>

**Cited in plan:** `docs/plan-2026-08-12.md` (adversarial questions,
risks)

## One-sentence summary

Standard duplicate-video pipelines follow a three-stage pattern —
metadata → visual perceptual hash (DCT on keyframes, ~64-bit) →
audio fingerprint (Chromaprint / spectral peaks) — and it maps
cleanly onto our current metadata-only stage. We can ship a
**metadata-only dedup proxy** today and reserve the visual/audio
layers for a compute-heavy v2.

## Why it matters to us

- The seed harness computes `unique_authors` as a diversity proxy,
  which is weak: the Blender Foundation's *Elephants Dream* on
  archive.org and on `video.blender.org` share an author but are the
  same video. That double-counts `total_duration_s`.
- Metadata dedup is cheap and offline-friendly: `(rounded_duration,
  normalized_title_ngrams, license_class)` is a good starting key.
- The 2-stage escalation pattern (metadata → visual → audio) is what
  every open-source dedup pipeline converges on (ViDupe, PDQ + akamhy,
  MediaLayer commercial API). We should replicate it.

## Ideation — how it changes what we ship

1. **Today (metadata-only):** add a `DedupReport` alongside
   `BenchmarkResult` with fields `n_cross_source_duplicates` and
   `n_within_source_duplicates`, keyed by `(duration_bucket_60s,
   title_5gram_hash)`.
2. **v2 (opt-in, integration-only):** ship a `dedup.visual` module
   backed by `videohash` (which uses `yt-dlp` internally, so it is
   gated on live download permission). Emits a 64-bit hash per
   record; Hamming distance ≤ 8 counts as a duplicate.
3. **v3 (opt-in, integration-only):** audio fingerprint via
   Chromaprint bindings. Only reachable via
   `SPECINT_RUN_INTEGRATION=1`.

## Risks

- Perceptual hashing is *not* license-safe by itself: we still need
  redistribution rights before extracting frames. Dedup happens
  *before* any download decision, so the hash step must be gated.
- Videohash is unstable across large rotations / mirror flips — fine
  for our use case but worth documenting.
- False positives across a 64-bit hash space are non-trivial at
  billion-scale. Escalate to audio fingerprint before merging
  records.
