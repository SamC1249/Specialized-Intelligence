from datetime import UTC, datetime

from specint.compare.ablation import _default_variants, ablation_matrix, run_ablation
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="A knife-skills demo — chop, dice, mince, slice",
        description="Chop onions. Dice carrots. Slice peppers. Mince garlic. Toss and serve.",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
        license=License.CC_BY,
        duration_s=300.0,
        height=720,
        recipe_steps=["Chop", "Dice", "Slice", "Mince"],
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_run_ablation_is_deterministic_and_covers_default_variants():
    query = SourceQuery(terms=["cooking"], max_results=5)
    by_source = {
        "a": [_rec(id="a:1")],
        "b": [_rec(id="b:1", license=License.RESTRICTED)],
    }
    runs_first = run_ablation(query, by_source)
    runs_second = run_ablation(query, by_source)

    assert [r.variant for r in runs_first] == list(_default_variants().keys())
    for a, b in zip(runs_first, runs_second, strict=True):
        assert a.variant == b.variant
        assert [row.mean_quality for row in a.rows] == [row.mean_quality for row in b.rows]


def test_ablation_variants_differentiate_procedural_records():
    query = SourceQuery(terms=["cooking"])
    procedural = _rec(id="proc:1", license=License.UNKNOWN)
    lean = _rec(
        id="lean:1",
        title="Untitled",
        description="",
        recipe_steps=[],
        license=License.UNKNOWN,
    )
    by_source = {"proc": [procedural], "lean": [lean]}
    runs = run_ablation(query, by_source)

    per_variant_total = {
        r.variant: next(row.mean_quality for row in r.rows if row.source == "__total__")
        for r in runs
    }
    assert per_variant_total["procedural_heavy"] > per_variant_total["license_heavy"]


def test_ablation_matrix_payload_is_json_ready():
    query = SourceQuery(terms=["cooking"])
    runs = run_ablation(query, {"a": [_rec()]})
    payload = ablation_matrix(runs)
    assert set(payload["mean_quality_matrix"].keys()) == {r.variant for r in runs}
    for _var, per_source in payload["mean_quality_matrix"].items():
        for source, mq in per_source.items():
            assert isinstance(source, str)
            assert 0.0 <= mq <= 1.0
    assert all("variant" in v and "weights" in v for v in payload["variants"])
