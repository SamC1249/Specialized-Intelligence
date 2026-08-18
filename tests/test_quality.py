from datetime import UTC, datetime

from specint.quality import score_record, score_records
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="Some cooking video",
        description="",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_score_minimum_record_is_low():
    r = _rec()
    assert 0.0 <= score_record(r) < 0.2


def test_score_uses_license_and_resolution():
    bare = _rec()
    rich = _rec(
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        description="A 5-minute knife skills tutorial." * 10,
        recipe_steps=["chop", "saute", "deglaze"],
    )
    assert score_record(rich) > score_record(bare)
    assert score_record(rich) > 0.7


def test_score_records_attaches_quality():
    r = _rec(license=License.CC0, duration_s=300.0, height=1080)
    [scored] = score_records([r])
    assert scored.quality_score is not None
    assert 0.0 <= scored.quality_score <= 1.0


def test_resolution_ladder_covers_all_tiers():
    from specint.quality.metrics import _score_resolution

    assert _score_resolution(_rec(height=None)) == 0.0
    assert _score_resolution(_rec(height=0)) == 0.0
    assert _score_resolution(_rec(height=1080)) == 1.0
    assert _score_resolution(_rec(height=720)) == 0.8
    assert _score_resolution(_rec(height=480)) == 0.5
    assert _score_resolution(_rec(height=240)) == 0.2


def test_text_density_is_zero_for_empty_record():
    from specint.quality.metrics import _score_text_density

    r = _rec(title="")
    assert _score_text_density(r) == 0.0


def test_duration_decays_beyond_target():
    from specint.quality.metrics import _score_duration

    assert _score_duration(_rec(duration_s=None)) == 0.0
    assert _score_duration(_rec(duration_s=0.0)) == 0.0
    assert _score_duration(_rec(duration_s=300.0)) == 1.0
    long_score = _score_duration(_rec(duration_s=1200.0))
    assert 0.0 < long_score < 1.0
