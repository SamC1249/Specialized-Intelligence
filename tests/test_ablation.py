from __future__ import annotations

from datetime import UTC, datetime

from specint.compare import run_ablation
from specint.domains import COOKING
from specint.records import License, Provenance, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="A demo",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
    )
    base.update(overrides)
    return VideoRecord(**base)


def _good(idx: int) -> VideoRecord:
    return _rec(
        id=f"good:{idx}",
        url=f"https://example.test/g/{idx}",
        title="Boil pasta then saute garlic",
        description="Boil water, cook pasta, saute garlic, toss with butter.",
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        recipe_steps=["boil", "cook", "saute", "toss"],
    )


def _bad(idx: int) -> VideoRecord:
    return _rec(
        id=f"bad:{idx}",
        url=f"https://example.test/b/{idx}",
        title="Movie trailer",
        description="",
        license=License.UNKNOWN,
        duration_s=5.0,
        height=240,
        recipe_steps=[],
    )


def test_ablation_reports_have_expected_shape():
    records = [_good(i) for i in range(3)] + [_bad(i) for i in range(3)]
    result = run_ablation(records, domain=COOKING)
    assert result["domain"] == "cooking"
    assert result["n_records"] == 6
    assert result["n_good"] == 3

    for name in ("v1", "v2", "v2_drop_license_tier", "v2_drop_procedural_density"):
        assert name in result["variants"], f"missing variant {name}"
        stats = result["variants"][name]
        assert set(stats) >= {
            "n",
            "n_good",
            "mean_good",
            "mean_bad",
            "separation",
            "kendall_tau",
        }


def test_v1_and_v2_rank_good_above_bad_kendall_tau_positive():
    records = [_good(i) for i in range(4)] + [_bad(i) for i in range(4)]
    result = run_ablation(records, domain=COOKING)
    v1_tau = result["variants"]["v1"]["kendall_tau"]
    v2_tau = result["variants"]["v2"]["kendall_tau"]
    assert v1_tau > 0.5
    assert v2_tau > 0.5


def test_dropping_license_tier_changes_v2_scores():
    """We do not claim dropping license_tier must *reduce* separation on
    every fixture — on our toy set the duration/resolution axes already
    dominate — but the ablation must observe a non-trivial delta so we
    know the weight is not dead code."""
    records = [_good(i) for i in range(4)] + [_bad(i) for i in range(4)]
    result = run_ablation(records, domain=COOKING)
    v2_sep = result["variants"]["v2"]["separation"]
    drop_sep = result["variants"]["v2_drop_license_tier"]["separation"]
    assert abs(v2_sep - drop_sep) > 1e-3


def test_dropping_license_tier_reduces_separation_when_it_is_the_only_signal():
    """Constructed fixture where license is the only discriminator:
    ablation must then strictly hurt separation."""
    good = [
        _rec(
            id=f"g:{i}",
            url=f"https://example.test/g/{i}",
            title="prepare mix cook simmer serve",
            description="prepare mix cook simmer serve",
            license=License.CC_BY,
            duration_s=300.0,
            height=1080,
            recipe_steps=["prepare", "mix", "cook", "simmer"],
        )
        for i in range(4)
    ]
    bad = [
        _rec(
            id=f"b:{i}",
            url=f"https://example.test/b/{i}",
            title="prepare mix cook simmer serve",
            description="prepare mix cook simmer serve",
            license=License.RESTRICTED,
            duration_s=300.0,
            height=1080,
            recipe_steps=["prepare", "mix", "cook", "simmer"],
        )
        for i in range(4)
    ]
    from specint.quality.metrics import WEIGHTS_V2, score_record_v2

    v2 = [score_record_v2(r) for r in good + bad]
    zeroed = {k: (0.0 if k == "license_tier" else v) for k, v in WEIGHTS_V2.items()}
    ablated = [score_record_v2(r, weights=zeroed) for r in good + bad]

    from statistics import fmean

    good_v2 = fmean(v2[:4])
    bad_v2 = fmean(v2[4:])
    good_abl = fmean(ablated[:4])
    bad_abl = fmean(ablated[4:])
    assert (good_v2 - bad_v2) > (good_abl - bad_abl)


def test_v2_differentiates_unknown_records_by_procedural_density_where_v1_cannot():
    """v1 uses `has_steps` as a step-function; v2 adds a graded verb-density
    signal. On two UNKNOWN-license records identical except for verb-rich
    text, v2 must open a gap larger than v1's."""
    unknown_rich = _rec(
        id="u:rich",
        url="https://example.test/u/rich",
        title="chop garlic saute onions simmer stock reduce sauce",
        description="Chop, saute, simmer, reduce — four procedural moves.",
        license=License.UNKNOWN,
        duration_s=300.0,
        height=1080,
        recipe_steps=["chop garlic", "saute onions", "simmer stock", "reduce sauce"],
    )
    unknown_poor = _rec(
        id="u:poor",
        url="https://example.test/u/poor",
        title="video",
        description="",
        license=License.UNKNOWN,
        duration_s=300.0,
        height=1080,
        recipe_steps=[],
    )

    from specint.quality import score_record_v1, score_record_v2

    v1_gap = score_record_v1(unknown_rich) - score_record_v1(unknown_poor)
    v2_gap = score_record_v2(unknown_rich, domain=COOKING) - score_record_v2(
        unknown_poor, domain=COOKING
    )
    assert v2_gap > v1_gap, (v1_gap, v2_gap)
