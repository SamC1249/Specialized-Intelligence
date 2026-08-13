from datetime import UTC, datetime

from specint.dedupe import (
    dedupe,
    dedupe_by_source,
    fingerprint,
    overlap,
)
from specint.records import License, Provenance, VideoRecord


def _rec(
    id_: str,
    source: str,
    title: str,
    duration_s: float | None = None,
    license_: License = License.UNKNOWN,
    quality: float | None = None,
) -> VideoRecord:
    return VideoRecord(
        id=id_,
        source=source,
        source_native_id=id_.split(":")[-1],
        url=f"https://example.test/{id_}",
        title=title,
        duration_s=duration_s,
        license=license_,
        provenance=Provenance(extractor="t", fetched_at=datetime.now(UTC), query=""),
        quality_score=quality,
    )


def test_fingerprint_is_stable_and_normalises():
    a = _rec("a:1", "a", "Cooking Pasta Carbonara!", duration_s=310)
    b = _rec("b:1", "b", "cooking-pasta-carbonara", duration_s=305)
    c = _rec("c:1", "c", "Cooking Pasta Carbonara", duration_s=800)
    assert fingerprint(a) == fingerprint(b)
    assert fingerprint(a) != fingerprint(c)


def test_fingerprint_synthesises_key_for_empty_title():
    r = _rec("x:42", "x", "", duration_s=60)
    k, _ = fingerprint(r)
    assert k.startswith("__id__:x:")


def test_dedupe_collapses_and_prefers_higher_quality():
    records = [
        _rec("wm:1", "wikimedia", "Knife skills demo", 45, License.CC0, quality=0.9),
        _rec("ia:1", "archive_org", "knife-skills demo", 46, License.CC_BY, quality=0.4),
    ]
    unique, collapsed = dedupe(records)
    assert collapsed == 1
    assert len(unique) == 1
    assert unique[0].id == "wm:1"


def test_dedupe_by_source_awards_winner_to_owning_source():
    by_source = {
        "wikimedia": [_rec("wm:2", "wikimedia", "Modern Chef", 260, License.CC_BY, quality=0.8)],
        "archive_org": [
            _rec("ia:2", "archive_org", "modern chef", 269, License.CC_BY, quality=0.3)
        ],
    }
    winners, collapsed = dedupe_by_source(by_source)
    assert collapsed == 1
    assert len(winners["wikimedia"]) == 1
    assert winners["archive_org"] == []


def test_overlap_matrix_reports_shared_fingerprints():
    by_source = {
        "wikimedia": [_rec("wm:3", "wikimedia", "Knife skills demo", 45, License.CC0, quality=0.9)],
        "archive_org": [
            _rec("ia:3", "archive_org", "knife-skills demo", 46, License.CC_BY, quality=0.4)
        ],
        "peertube": [_rec("pt:1", "peertube", "Something Else", 100, License.CC_BY, quality=0.5)],
    }
    payload = overlap(by_source)
    assert payload["total_records"] == 3
    assert payload["unique_fingerprints"] == 2
    pair = next(p for p in payload["pairs"] if {p["a"], p["b"]} == {"wikimedia", "archive_org"})
    assert pair["shared"] == 1
    assert pair["jaccard"] > 0.0
    other = next(p for p in payload["pairs"] if {p["a"], p["b"]} == {"peertube", "wikimedia"})
    assert other["shared"] == 0
