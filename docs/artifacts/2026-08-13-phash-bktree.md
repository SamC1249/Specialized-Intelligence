# Perceptual-Hash + BK-Tree / Banded-LSH — CPU-only Near-Duplicate Detection

- Reference implementation write-up: `dev.to/…/perceptual-hash-pipeline`
  (2025).
- Related academic work: "Fast Video Deduplication and Localization With …",
  NSF Access #10613771 (2024).
- Read on: 2026-08-13 (by `Adversarial-Agent`).

## One-paragraph summary

Perceptual hashing (pHash via a 32×32 DCT low-frequency block, dHash,
aHash) reduces a video frame to a 64-bit signature that survives
re-encoding, mild colour shifts, and modest scaling. Aggregating a fixed
number of *keyframes* per video into a per-camera fingerprint gives an
integer-only representation suitable for large-scale storage.
Sub-linear candidate retrieval uses either a BK-tree over Hamming distance
or **banded LSH** — split the 64-bit hash into four 16-bit bands and index
each band; by the pigeonhole principle, hashes within 3 bits of Hamming
distance share at least one identical band.

## Why we care

For the *download-and-store* phase of Specialized-Intelligence, this is the
cheapest and legally-safest tier-2 dedup:

- No ML model, no GPU, no dependency on a proprietary vector DB.
- Hashes are irreversible: we can throw away the frame after hashing, which
  helps our license story (we never redistribute a CC-BY-NC frame; we only
  keep its 64-bit fingerprint for dedup).
- Integrates cleanly with a plain SQLite (or Postgres) index, matching our
  future `db_structured.md` roadmap for a shared record store.

## Ideas we can borrow

- **Fixed-K keyframe fingerprint.** Sample K evenly-spaced keyframes per
  video (default K=16 in forge/dedup). Normalises the fingerprint size
  across videos of different lengths.
- **Banded LSH before BK-tree.** Use banded LSH as a coarse filter (indexed
  in SQLite, no extra process), then confirm with per-band Hamming distance.
  Fits our CPU-only, no-daemon design constraint.
- **Cross-camera / cross-source union-find.** For multi-cam or multi-source
  duplicates (Wikimedia → Internet Archive re-uploads, PeerTube federation),
  compute the fingerprint independently per source and union-find them
  during aggregate.

## Interaction with our current metadata-only dedup

The metadata digest we ship today (title-norm + duration-bucket +
author-norm) is orthogonal:

- Metadata digest is a **false-negative-tolerant** filter (misses re-titled
  re-uploads).
- pHash + BK-tree is a **false-positive-tolerant** filter (misses only when
  the video is heavily edited).

Correct order once we start storing frames:
1. Metadata dedup — free, instant, ~50 % of the win.
2. pHash-BK dedup — cheap, catches most re-encodes.
3. Embedding-based dedup (MLT-Dedup style) — only where the above two
   demonstrably leak.

## Concrete follow-up items filed

- `docs/plan-2026-08-13.md` § "Attack list" item 8.
- No code shipped in this run.
