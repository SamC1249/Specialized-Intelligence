# OpenVid-1M + VideoUFO — CC-BY-4.0 packaged corpora

- **OpenVid-1M:** Nan et al., ICLR 2025.
  <https://doi.org/10.48550/arxiv.2407.02371>
  <https://huggingface.co/datasets/nkp37/OpenVid-1M>
- **VideoUFO:** Wang & Yang, NeurIPS D&B 2025.
  <https://huggingface.co/datasets/WenhaoWang/VideoUFO>

## What they are

Two 2024–2025 million-scale text-to-video corpora, both released under
CC-BY-4.0. OpenVid-1M contains 1,019,957 clips (avg ~7.2s, min
resolution 512×512) with a 433K subset ("OpenVidHD-0.4M") at 1080p.
VideoUFO contains 1.09M clips across 1,291 user-focused topics with
six per-clip quality scores.

## Why they matter for Specialized-Intelligence

They are **not** sources to re-scrape — they are already packaged.
Their role here is:

1. **Comparison targets.** Prove that our metadata-only, source-agnostic
   crawl finds videos these curated corpora *did not* (novel yield) at
   comparable quality. If we cannot beat them on any subset, our
   pipeline is not adding value.
2. **Calibrators for the quality scorer.** Both publish per-clip
   quality/aesthetic scores; we can regress our metadata-only score
   against theirs on the overlap set. Good calibration = evidence
   that metadata heuristics predict downstream utility (H5 in the
   plan).
3. **Duration distribution reference.** Both corpora have a very
   different duration profile from cooking (7s clips vs. 8–30 min
   procedural videos). Confirms that the duration curve is
   domain-dependent — supports the **W9** deliverable.

## Concrete implementation ideas

- `src/specint/compare/external.py` — loader for OpenVid-1M and
  VideoUFO **metadata Parquet files only** (no video download). Emits
  a virtual `BenchmarkResult` row so `python -m specint compare` can
  include them as reference bars.
- Overlap detector: use the youtube-channel-id or the SHA of the
  OpenVid `caption` field to find our records that match theirs.
  Report `n_novel` = records we found and they did not.
- **Do not** commit any of their sample clips to our repo. Metadata
  Parquets are small (~200 MB) and downloadable at CI-runtime; the
  fixture path is a synthetic mini-Parquet of ~50 rows we can commit.
