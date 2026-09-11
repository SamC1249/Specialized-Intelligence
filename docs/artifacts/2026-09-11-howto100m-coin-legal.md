# HowTo100M / COIN / CrossTask — cautionary notes on "public" datasets

- **Citations.**
  - HowTo100M (Miech et al. 2019) — 136M clips / 1.2M YouTube videos.
    HuggingFace mirror reports "license: not specified".
  - COIN (Tang et al., Tsinghua/Meitu) — 11,827 YouTube videos,
    180 tasks, 12 domains. License: research-only, no endorsement.
  - CrossTask (Zhukov et al. 2019) — 83 tasks; the 2022 README notes
    many source videos are already dead-linked and the authors
    re-host them under an unspecified license.

## One-paragraph summary

These are the three de-facto benchmarks for instructional video
understanding. All three are **YouTube-derived** and none of them are
Creative Commons at the source. The published corpora are lists of URLs
+ per-frame features; the raw videos are governed by whatever license
the uploader chose (usually the standard YouTube license) plus
YouTube's ToS. Their headline "MIT license" applies only to the
annotations / features files, not to the underlying media.

## Why it matters to Specialized-Intelligence

- This is exactly the failure mode our repo must avoid: shipping a
  dataset that is technically-a-URL-list but where the practical use
  requires downloading YouTube video under standard license. Under our
  hard constraints (AGENTS.md §1) we cannot re-use HowTo100M as a
  training set, only as an *evaluation-side* benchmark of what we
  *cannot* legally reproduce.
- However, HowTo100M's URL list is public. We can:
  1. Take the intersection of HowTo100M video IDs with YouTube Data
     API `videoLicense=creativeCommon` — those IDs *are* legally
     re-usable (subject to CC-BY attribution). This is the fastest
     legal upgrade to our current source mix.
  2. Use HowTo100M's activity taxonomy (cooking / hand crafting / etc.)
     to seed our multi-domain expansion plan without any data reuse.
- COIN's research-only license is a red flag; do not import.

## Concrete ideas to steal

- Add a new source adapter `youtube_cc` that hits YouTube Data API v3
  `search.list?type=video&videoLicense=creativeCommon` and stores URL
  + metadata **only** (no download). Media_url stays `None` unless we
  later add a per-video CC-BY verification pass.
- Ship a `datasets/known_urllists/` folder that ingests public URL
  lists (HowTo100M etc.) and produces a `known_id_set.txt`; a filter
  can then intersect with YouTube API CC listings and emit only the
  legally-reusable subset. This gives us an audit trail: "of the 1.2M
  HowTo100M videos, N are still up AND CC-licensed as of YYYY-MM-DD".
- Add license classification to CI as a *guard*: if any `VideoRecord`
  has `license=UNKNOWN` AND `media_url is not None`, fail the build.
  This turns the invariant "no unlicensed media redistribution" into
  a hard test, not a code review convention.

## Risks / gotchas

- CC status on YouTube can be revoked or changed after the fact.
  Snapshot the `license` field per fetch and re-verify before every
  training run.
- YouTube's ToS still governs API usage even for CC videos. Rate
  limits, attribution requirements, and no-bulk-download rules apply.
- Do NOT download media from `youtube_cc` adapter in this repo. We are
  URL + metadata only; media handling is a separate downstream
  concern with its own legal review.
