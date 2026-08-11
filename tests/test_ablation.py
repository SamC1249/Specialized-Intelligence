from datetime import UTC, datetime

from specint.compare import ablate, to_report
from specint.compare.ablation import PRESETS
from specint.records import License, Provenance, SourceQuery, VideoRecord


def _rec(**overrides) -> VideoRecord:
    base = dict(
        id="t:1",
        source="t",
        source_native_id="1",
        url="https://example.test/1",
        title="cooking recipe how to",
        description="Step by step: chop the onion and saute with butter.",
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
        license=License.CC_BY,
        duration_s=300.0,
        height=1080,
        recipe_steps=["chop", "saute"],
    )
    base.update(overrides)
    return VideoRecord(**base)


def test_ablate_returns_row_per_preset_per_source():
    q = SourceQuery(terms=["cooking"], max_results=5)
    r1 = _rec()
    r2 = _rec(id="t:2", source_native_id="2", license=License.UNKNOWN)
    rows = ablate(q, {"src_a": [r1, r2], "src_b": [r1]})
    presets = {row["preset"] for row in rows}
    assert presets == set(PRESETS.keys())
    sources = {row["source"] for row in rows}
    assert sources == {"src_a", "src_b"}
    for row in rows:
        assert 0.0 <= row["mean_quality"] <= 1.0


def test_ablation_report_declares_winner():
    q = SourceQuery(terms=["cooking"], max_results=5)
    rows = ablate(q, {"src_a": [_rec()]})
    report = to_report(q, rows, notes="unit")
    assert "summary" in report
    assert report["summary"]["winner"]["preset"] in PRESETS
    assert report["summary"]["winner"]["mean_quality"] > 0.0


def test_ablation_differentiates_weight_vectors():
    q = SourceQuery(terms=["cooking"], max_results=5)
    non_lang = _rec(title="video 1", description="")
    rows = ablate(q, {"src_a": [non_lang]})
    means = {row["preset"]: row["mean_quality"] for row in rows}
    assert len(set(round(v, 6) for v in means.values())) > 1
