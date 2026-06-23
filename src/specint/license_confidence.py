"""Per-record license-confidence scoring.

Adversarial-Agent's day-one plan §7.6 flagged the long tail of
license-ambiguous records (e.g. a Wikimedia upload tagged CC-BY at the
file level but with a "non-commercial only" string in the description).
This module attaches an explicit confidence in [0, 1] to every record so
downstream curators can threshold rather than naively trust the SPDX-ish
tag the adapter coerced.

Inputs / outputs:
  - `score_license_confidence(record) -> float in [0, 1]`
  - `tag_records(records) -> list[tuple[VideoRecord, float]]`

The score is deliberately a *coarse* heuristic; the real fix is per-source
adapter improvements + human spot checks. The confidence value should be
written to manifests as `license_confidence` so we can re-rank later.

Rules (additive, capped at 1.0):
  * Adapter declared a redistributable license (CC0/CC-BY/CC-BY-SA/PD):
      base 0.6.
  * License URL resolves to a recognised Creative-Commons or PD pattern:
      +0.2.
  * Description / title does NOT contain a contradicting phrase
      (e.g. "non-commercial", "all rights reserved", "do not redistribute"):
      +0.2. Contradiction => clamp to <=0.2.
  * Source is known-clean (Wikimedia Commons, Internet Archive
    PD/Community Video, government open archives): +0.1.

`License.UNKNOWN` is always 0.0. `License.RESTRICTED` is always 0.0.
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.records import License, VideoRecord

CC_URL_PATTERNS = (
    "creativecommons.org/licenses/",
    "creativecommons.org/publicdomain/",
    "rightsstatements.org/page/NoC-US/",
    "creativecommons.org/publicdomain/mark/",
)

CONTRADICTION_PHRASES = (
    "non-commercial",
    "noncommercial",
    "non commercial",
    "all rights reserved",
    "do not redistribute",
    "no redistribution",
    "personal use only",
    "academic use only",
    "research use only",
)

KNOWN_CLEAN_SOURCES = {
    "wikimedia",
    "wikimedia_commons",
    "archive_org",
    "internet_archive",
    "gov_open",
    "flickr_pd",
}


def _has_contradiction(text: str | None) -> bool:
    if not text:
        return False
    needle = text.lower()
    return any(phrase in needle for phrase in CONTRADICTION_PHRASES)


def _license_url_score(url: str | None) -> float:
    if not url:
        return 0.0
    lowered = url.lower()
    return 0.2 if any(p in lowered for p in CC_URL_PATTERNS) else 0.0


def score_license_confidence(record: VideoRecord) -> float:
    if record.license in (License.UNKNOWN, License.RESTRICTED):
        return 0.0
    if not record.license.is_redistributable:
        return 0.0

    score = 0.6

    license_url = str(record.license_url) if record.license_url else None
    score += _license_url_score(license_url)

    contradicted = _has_contradiction(record.title) or _has_contradiction(record.description)
    if contradicted:
        # Strong evidence of mismatch; cap aggressively.
        return min(score, 0.2)
    score += 0.2

    if record.source in KNOWN_CLEAN_SOURCES:
        score += 0.1

    return min(score, 1.0)


def tag_records(records: Iterable[VideoRecord]) -> list[tuple[VideoRecord, float]]:
    return [(r, score_license_confidence(r)) for r in records]


def filter_by_confidence(
    records: Iterable[VideoRecord], threshold: float = 0.5
) -> list[VideoRecord]:
    """Keep only records whose license confidence is >= threshold."""
    return [r for r, c in tag_records(records) if c >= threshold]
