"""Training-corpus eligibility filter.

Addresses risk #1 from `docs/plan-2026-06-20.md` ("License classification
is heuristic; we may mislabel a Commons video uploaded under a
non-redistributable license. Mitigation: default to `License.UNKNOWN`
and exclude from training corpora.") by making the exclusion *explicit*
rather than implicit, and by covering it with a test
(`tests/test_safety.py`).

Hard rules:

- `License.UNKNOWN` is never eligible, even if a human later believes
  the record is probably CC. If the record is actually free, re-classify
  it upstream in the adapter; do not weaken this filter.
- `License.RESTRICTED` is never eligible.
- CC-BY and CC-BY-SA require a non-empty `author` string, because the
  license is only satisfiable with attribution.
- CC0 and `PUBLIC_DOMAIN` and `OTHER_FREE` are eligible even without
  an author.
"""

from __future__ import annotations

from collections.abc import Iterable

from specint.records import License, VideoRecord

ATTRIBUTION_REQUIRED: frozenset[License] = frozenset({License.CC_BY, License.CC_BY_SA})


def training_eligible(record: VideoRecord) -> bool:
    lic = record.license
    if lic in {License.UNKNOWN, License.RESTRICTED}:
        return False
    if not lic.is_redistributable:
        return False
    return not (lic in ATTRIBUTION_REQUIRED and not (record.author or "").strip())


def filter_for_training(records: Iterable[VideoRecord]) -> list[VideoRecord]:
    return [r for r in records if training_eligible(r)]
