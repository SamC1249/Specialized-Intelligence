# Perceptual video hashing for near-duplicate detection

- **Sources.**
  - `akamhy/videohash` — 64-bit wavelet-hash-of-collage perceptual hash.
  - Backblaze `videohash-deduplication` sample — union-find clustering
    over Hamming distance.
  - Two DEV.to write-ups on dHash + LSH banding for O(√n) candidate
    generation.
- **Claim we care about.** For any web-scale video corpus, *near-duplicate
  suppression* is a first-order problem, not a nice-to-have. Standard
  practice is a 64-bit perceptual hash + LSH-banded index; typical
  precision/recall on cooking re-uploads sits at ~94 % TPR / <1 % FPR with a
  Hamming threshold of ≤ 8 out of 64.

## Method summary

- Sample 1 frame per second (or N=8 keyframes), resize to a canonical
  square, compute wavelet or DCT-based hash on either each frame or a
  frame collage.
- Store 64-bit signatures in SQLite (WAL mode) with LSH bands of 4×16
  bits. To find near-duplicates, query on exact band matches and re-rank
  by Hamming distance.
- Union-find over pairwise "within threshold" edges collapses the graph
  into clusters; you keep one canonical member per cluster.

## What it changes for us

1. **We are pre-download.** All our current work is metadata-only, so
   frame-perceptual hashes are out of scope until we start downloading.
   *But* we should reserve a stable `fingerprint: str | None` field on
   `VideoRecord` (perceptual hash as hex when known, else `None`), so
   downstream downloaders can populate it without a schema migration.
2. **Metadata-only dedup baseline.** Ship
   `specint.quality.dedup.dedupe_by_id_and_title(records)` today. It only
   needs to drop exact `id` collisions and near-identical titles (case-
   folded + punctuation-stripped). Include it in the harness so
   cross-source dupes show up in the report.
3. **Do not require perceptual hashing in unit tests.** `videohash`
   pulls `ffmpeg` and yt-dlp — heavy and network-oriented. Keep it as an
   optional extra behind an `[dev-perceptual]` dependency group when we
   need it, not a hard dep.

## Risks / disagreements

- Perceptual hashes are attackable by adversarial re-encodes. For a
  training corpus that's fine (an attacker gains us their video for free);
  for takedown pipelines it isn't. Not relevant to our current mission.
- 1-fps sampling misses very short clips (< 1 s). Cooking is usually
  ≫ 30 s so acceptable, but flag it if we ever ingest micro-clip sources.
