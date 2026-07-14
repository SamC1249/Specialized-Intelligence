# Panda-70M desirability filters — metadata-only projections

- **Dataset**: Panda-70M. 70M video-caption pairs. Not directly usable
  under our constraints (YouTube-sourced), but its **filter taxonomy**
  is a design north-star.
- **Six desirability categories** used to shrink 70M → high-quality
  10M subset:
  1. `desirable` (80.5%)
  2. `0_low_desirable_score` (5.28%)
  3. `1_still_foreground_image` (6.82%)
  4. `2_tiny_camera_movement` (1.20%)
  5. `3_screen_in_screen` (5.03%)
  6. `4_computer_screen_recording` (1.13%)
- **Shot boundary detection** via TransNetV2 keeps only videos with
  meaningful cuts (or, for single-shot filtering, exactly one).

## Why it matters

Roughly one video in five gets rejected by these filters even after
initial curation. The most common rejections (still image, tiny
camera movement, screen recording, screen-in-screen) are **detectable
from metadata alone** with reasonable precision:

| Panda-70M category           | Metadata proxy                                                            |
| ---------------------------- | ------------------------------------------------------------------------- |
| `1_still_foreground_image`   | Title contains "slideshow", "compilation", or duration ≈ n × single-image |
| `3_screen_in_screen`         | Title/description mentions "reaction", "commentary", "PIP"                |
| `4_computer_screen_recording`| Title mentions "tutorial", "how-to-install"; MIME=screen-capture codec     |
| `2_tiny_camera_movement`     | Aspect ratio + "static camera" tags on PeerTube                           |
| `0_low_desirable_score`      | Fallback to composite quality score < threshold                           |

None of these are perfect, but they're free.

## Concrete hooks into this repo

1. Add a **`quality/negative_signals.py`** module that returns a list
   of "penalty tags" applied to a `VideoRecord`. Each tag decrements
   the composite score by a small, documented amount.
2. Introduce a **`penalty_tags: list[str]`** field on `VideoRecord`
   (default `[]`). Coding-Agent bumps schema version in
   `db_structured.md`.
3. Add per-tag counters to `BenchmarkResult` so we can see e.g. "23%
   of `archive_org` cooking records look like slideshows".
4. Downstream, plan a shot-boundary check using TransNetV2 only on the
   top-K candidates promoted by metadata triage (frame-sampled stage
   from the DenseStep2M artifact).
