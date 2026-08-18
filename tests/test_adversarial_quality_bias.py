"""H3 — schema-availability bias in the quality scorer.

Two records with identical *actual* provenance (both CC-BY, 5 minutes,
1080p, same title/description) should score identically regardless of
which upstream source they came from. Today they do not: the
`_score_resolution` component reads `record.height`, which
`archive_org.py` structurally does not populate even for videos whose
underlying media is 1080p. Result: archive_org records get a
0 * 0.20 = 0 contribution from resolution, while peertube records get
1 * 0.20 = 0.20.

This test locks the bias in place as an `xfail` — when a future scorer
normalises for schema availability, the assertion below will become
true and the `xfail` will `XPASS`, prompting a follow-up.

DO NOT weaken the assertion. If it starts passing, the correct action
is to remove the `xfail` marker and update the plan.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from specint.quality import score_record
from specint.records import License, Provenance, VideoRecord


def _synth(source: str, *, height: int | None) -> VideoRecord:
    return VideoRecord(
        id=f"{source}:x",
        source=source,
        source_native_id="x",
        url=f"https://example.test/{source}/x",
        media_url=f"https://cdn.example.test/{source}/x.mp4",
        title="Knife skills tutorial",
        description="A five-minute knife-skills demonstration." * 3,
        duration_s=300.0,
        height=height,
        license=License.CC_BY,
        author="Test Author",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )


@pytest.mark.xfail(
    reason=(
        "H3: schema-availability bias. archive_org does not populate height "
        "even when the underlying video is 1080p, so the resolution component "
        "of the score is unfairly zero. Tracked in docs/plan-2026-08-18.md."
    ),
    strict=True,
)
def test_identical_semantics_should_score_identically_across_sources():
    peertube_like = _synth("peertube", height=1080)
    archive_like = _synth("archive_org", height=None)  # actually 1080p, but no field
    assert score_record(peertube_like) == pytest.approx(score_record(archive_like), abs=1e-6)
