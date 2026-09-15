# panda70m-desirability — six categories that make a video unfit for training

Source: [Snap Research Panda-70M](https://github.com/snap-research/Panda-70M/blob/main/README.md).
The dataset itself is YouTube-seeded and not redistributable. The
useful contribution here is the **six-way `desirable` schema** the
paper introduces for filtering training videos.

## The six categories and their reported prevalence

| Class                          | % of raw   | Why it's bad for procedural training |
| ------------------------------ | ---------- | ------------------------------------ |
| `desirable`                    | 80.5%      | (baseline)                           |
| `0_low_desirable_score`        | 5.28%      | Mixed junk.                          |
| `1_still_foreground_image`     | 6.82%      | Static image + audio ⇒ no motion.    |
| `2_tiny_camera_movement`       | 1.20%      | Pan-and-scan of a still.             |
| `3_screen_in_screen`           | 5.03%      | Composited overlay ⇒ shifting frame boundary breaks depth/flow labels. |
| `4_computer_screen_recording`  | 1.13%      | Non-physical domain; distribution shift for world models. |

Shot boundaries are labelled with
[TransNetV2](https://github.com/soCzech/TransNetV2). A "single-shot"
video has a boundary list of length 1.

## Why the categories matter for cooking specifically

Cooking videos on the open web are heavy with `1_still_foreground_image`
(recipe cards where a still photo is overlaid on top of music) and
`3_screen_in_screen` (a picture-in-picture chef head). If we do not
filter these out, our `world-model` corpus will overfit to *slideshows
of food*, not procedural transformations of it.

## Metadata-only surrogates

Panda-70M's desirability model is a trained classifier over video
frames. We cannot ship it here. But each category has a metadata
proxy that is >0 correlation:

- `1_still_foreground_image` — `duration_s > 60 and recipe_steps == []
  and description contains "photo" | "slideshow"`.
- `2_tiny_camera_movement` — no metadata-only signal; punt.
- `3_screen_in_screen` — title contains an aspect-ratio marker or
  `"live" | "reaction" | "podcast"`; description mentions a co-host.
- `4_computer_screen_recording` — `title contains "screencast" |
  "tutorial recording"`; `keywords` intersects
  `{"screencast", "screen capture"}`.

Yield of these filters on our four current fixtures is nil (they were
seeded from high-quality Wikimedia / Commons video), so the filters
would ship as zero-op on the fixture baseline — an *appropriate*
outcome for a triage filter meant to fire on the long tail.

## How we'd use it here

- **`src/specint/quality/desirability.py`** (new, Coding-Agent PR):
  metadata-only classifier returning a `DesirabilityCategory` enum
  matching Panda-70M's six-way schema plus an `UNKNOWN` default.
- **`src/specint/records.py`** — add `desirability: DesirabilityCategory
  = UNKNOWN` to `VideoRecord`, defaulted so existing records still
  validate. Bump db_structured.md accordingly.
- **`src/specint/compare/harness.py`** — new `BenchmarkResult` column
  `n_desirable`; total-row `desirability_rate = n_desirable / n_records`.
- **`tests/fixtures/`** — add one *deliberately-bad* fixture per source
  (a slideshow, a screencast, a picture-in-picture) so the filter has
  a positive test signal.
