# YFCC100M — the CC-licensed video sub-corpus

## Citation

- Thomee et al. *YFCC100M: The New Data in Multimedia Research.* CACM /
  arXiv:1503.01817, 2016.
- Multimedia Commons (AWS Open Data):
  <https://registry.opendata.aws/multimedia-commons/> — public S3 bucket
  at `s3://multimedia-commons/`, no AWS account required for read.
- Core dataset page:
  <https://multimediacommons.wordpress.com/yfcc100m-core-dataset/>

## One-paragraph summary

YFCC100M is a 100M-item Flickr sample released under the *original
uploader's* Creative Commons license — a mix of CC-BY, CC-BY-SA, CC0,
CC-BY-NC (which we reject), and CC-BY-ND (which we also reject). The
video subset is **787,479 files ≈ 8,081 hours** (mean 37s, median 28s).
The Multimedia Commons project has re-derived and re-hosted these on an
AWS Open Data S3 bucket, with keyframes already extracted at 1 fps and
stored under `data/videos/keyframes/`. License information is per-file
in the metadata sidecar. About 5,957 videos and 34,876 images have
since been deleted by their owners; the corpus is stable but not
immutable.

## What it changes for `specint`

- **Highest expected yield** of any single license-clean video source
  we have identified. 8k hours is ~5× the currently observed license-
  clean yield from all of our current fixtures combined, and it comes
  with pre-extracted keyframes so we can skip a frame-extraction pass
  entirely for downstream ranking.
- Justifies a new adapter `src/specint/sources/yfcc100m.py` that reads
  the metadata TSV directly from S3 (`--no-sign-request`) and yields
  `VideoRecord`s with `media_url` set only when the per-file license is
  in `{CC0, CC_BY, CC_BY_SA, PD}`. Because the payload is a flat TSV,
  `parse()` can be tested entirely from a small offline fixture.
- Introduces the first source where **`fps` and `keyframe` info are
  known upstream**. We should extend `VideoRecord` (schema change → own
  plan entry) to carry `keyframe_dir: HttpUrl | None`; until then, stash
  it in `provenance.query`.
- Because YFCC100M content is *general* Flickr, cooking is a
  small-but-non-trivial sliver. This is a great forcing function for a
  keyword+embedding filtering pipeline; it also lets us measure how
  cooking-representation degrades on a generic corpus vs. our current
  cooking-seeded sources.

## Attack surface

- **License mislabelling by uploaders.** Flickr's own moderation is
  imperfect; a CC-BY tag on YFCC100M is a *claim*, not a guarantee.
  Our shared license classifier should downgrade to `UNKNOWN` when the
  YFCC100M metadata contradicts the actual license URL, and we should
  refuse to publish redistributable `media_url` for any record where the
  YFCC100M row and Flickr's live API disagree (checked periodically,
  not per-record).
- **Owner deletions.** 40k already-deleted items in a snapshot from
  2014 → 2024 implies churn of ~1% / decade. Any `specint`-derived
  corpus needs a "was the source still live at fetch time?" provenance
  bit; today's `Provenance.fetched_at` is not enough.
- **Cooking coverage is thin.** Median clip length of 28s means most
  clips are far shorter than the 5-min "procedural sweet spot" our
  quality scorer targets. Naïvely scoring YFCC100M against today's
  weights will under-score it and hide a real yield opportunity —
  motivates the quality-weight calibration hypothesis (future plan).
