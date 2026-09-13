# DataComp / CommonPool: the legal template we should copy

- Paper: *DataComp: In search of the next generation of multimodal
  datasets* (Gadre et al., NeurIPS 2023; arXiv:2304.14108).
- Follow-up critique: *A Common Pool of Privacy Problems* (Kim et al.,
  arXiv 2025) — https://doi.org/10.1145/3788646.3789521
- URL: https://arxiv.org/html/2304.14108v4

## The one-sentence legal template

> "CommonPool is distributed as an image URL-text pair index under a
> **CC-BY-4.0** licence. Our pool construction pipeline has four steps:
> URL extraction and data download, NSFW detection, evaluation set
> deduplication, and face blurring."

Read carefully: **the URL+metadata index is CC-BY**, the image bytes are
not. The critique paper (2025) confirms this is legally coherent so
long as (a) the model card says "research artefact", and (b) downstream
users know they inherit per-URL rights. That is exactly the posture we
need for cooking-video URLs + JSON-LD sidecars.

## Design choices we should mirror one-for-one

1. **We ship a *URL index*, never media bytes.** Our
   `serialize_records()` already does this — no `media_url` on
   non-redistributable records, no bulk mirror. Encode this explicitly
   in `db_structured.md` under a "Distribution" section.
2. **NSFW/CSAM filtering at *URL collection* stage, not download.**
   CommonPool applied classifiers before download so that CSAM was
   *never fetched*. Analogue for us: a `sources/*_prefilter.py` runs on
   the URL list itself (regex + domain block-list) before `search()`
   even hits a network.
3. **Face blurring on any derivative frame release.** If/when we start
   emitting frames (fair-use derivative), the pipeline must include a
   deterministic face-blurring pass and record its version in
   `Provenance.extractor_git`.
4. **Two competition tracks: "filter our pool" and "bring your own
   data".** DataComp fixes the training code and lets researchers
   compete on the *dataset*. Our `compare` CLI is the same idea in
   miniature: fix the scorer, vary the source mix, rank the resulting
   `mean_quality` and `n_license_clean`. We should promote this to a
   documented "filtering track" in `docs/roadmap.md`.

## What the 2025 critique warns us about

- **CC-BY on the index does not sanitize commercial use of models
  trained on the underlying content.** Our own README must contain the
  same disclaimer.
- **NSFW filters are recall-limited.** We should add both a
  domain-blocklist *and* a metadata heuristic (title/description
  regexes) and log both signals separately so we can measure drift.
- **Face-blurring is not privacy.** Full-body pose, tattoos, and
  location metadata still identify people. If we ever expand to
  surgery/lab domains (memory says we will), a stricter policy —
  research-use flag + no derivative frames — is required.

## Actionable

- Add a `Distribution` section to `db_structured.md` copying the four
  CommonPool rules above.
- Add a `LICENSE.dataset.md` covering the URL/metadata index as CC-BY-4.0
  and disclaiming per-URL rights. Not merged until Coding-Agent lands
  the P0 provenance PR.
