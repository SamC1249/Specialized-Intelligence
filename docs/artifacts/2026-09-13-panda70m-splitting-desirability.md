# Panda-70M: Semantics-aware splitting + desirability filtering

- Paper: *Panda-70M: Captioning 70M Videos with Multiple Cross-Modality
  Teachers* (Snap Research, CVPR 2024; arXiv:2402.19479).
- URL: https://arxiv.org/html/2402.19479
- Repo: https://github.com/snap-research/Panda-70M
- Data licence: upstream is HD-VILA-100M; per-clip licences inherit from
  YouTube uploaders → **not** in our allowlist for redistribution. We
  study the pipeline, not the corpus.

## The splitting algorithm (worth stealing)

The Panda-70M pipeline is a two-stage semantics-aware split:

1. **Shot boundary detection** with PySceneDetect (cheap) or TransNetV2
   (accurate).
2. **Adjacent-clip stitching** with ImageBind embeddings: adjacent clips
   whose frame embeddings are similar are merged so the average clip is
   ~8s instead of PySceneDetect's ~4s. Handles fade transitions and
   unedited long footage (recursively cut into 5s pieces if > 7s).

Reported Max-Running-LPIPS (lower = more consistent):

| Method                 | Max running LPIPS | Avg clip len |
| ---------------------- | ----------------: | -----------: |
| Subtitle alignment     | 0.408             | 11.8s        |
| Vanilla PySceneDetect  | 0.247             | 4.1s         |
| Two-stage splitting    | 0.256             | 7.9s         |

Two-stage almost matches PySceneDetect on consistency while doubling
usable clip length. This is *the* clip-level curation contract.

## The desirability filter (October 2024 update)

For video-*generation* training the team added a "desirability" filter
that rejects six failure modes with published prevalences:

| Bucket                          | Fraction |
| ------------------------------- | -------: |
| `desirable`                     | 80.5%    |
| `0_low_desirable_score`         | 5.28%    |
| `1_still_foreground_image`      | 6.82%    |
| `2_tiny_camera_movement`        | 1.20%    |
| `3_screen_in_screen`            | 5.03%    |
| `4_computer_screen_recording`   | 1.13%    |

The absolute numbers are noisy, but the *taxonomy* is right. Even at
metadata stage we can pre-flag `3_screen_in_screen` and
`4_computer_screen_recording` from title/description patterns
("screenshot", "screencast", "let's play", "unboxing my monitor"…).

## Actionable for specint

- **Do not decode media yet.** Everything above requires frame access.
  Keep it in a `docs/roadmap.md` future-phase section, and gate the
  frame-decode adapter behind an env var when it lands.
- **Do adopt the taxonomy.** Add `RejectReason` enum with entries
  aligned to Panda-70M's buckets plus our own additions
  (`non_video_mime`, `duration_too_short`, `duration_too_long`,
  `license_unknown`, `license_restricted`, `screen_recording_signal`,
  `still_image_signal`). This is compatible with SolarWM's
  `failure_reasons` field (see the SolarWM artefact).
- **Do write a fixture-driven test** proving that titles like
  "Screencast of my terminal" and "How to install VS Code — full
  screencast" get rejected by a metadata-only rule with reason
  `screen_recording_signal`, without needing any frames.
