import json
from pathlib import Path

from specint.cli import main


def test_cli_sources_lists_registry(capsys):
    rc = main(["sources"])
    assert rc == 0
    out = capsys.readouterr().out
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert slug in out


def test_cli_compare_fixtures_writes_json(tmp_path: Path, capsys):
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert "query" in payload
    assert "rows" in payload
    sources = {row["source"] for row in payload["rows"]}
    assert "__total__" in sources


def test_cli_compare_refuses_live_without_env(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    rc = main(["compare", "--terms", "cooking", "--output", str(tmp_path / "out.json")])
    assert rc == 2


def test_cli_compare_fixtures_actually_loads_records(tmp_path: Path):
    """--fixtures used to silently produce zero rows; it must load real records."""
    out = tmp_path / "report.json"
    rc = main(["compare", "--fixtures", "--terms", "cooking", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    total = next(r for r in payload["rows"] if r["source"] == "__total__")
    assert total["n_records"] > 0, "--fixtures must parse real fixture files"


def test_cli_domains_lists_profiles(capsys):
    rc = main(["domains"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cooking" in out
    assert "surgery" in out


def test_cli_compare_uses_domain_terms(tmp_path: Path):
    out = tmp_path / "report.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--domain",
            "cooking",
            "--language",
            "en",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["query"]["terms"], "domain profile must produce non-empty terms"


def test_cli_compare_diff_emits_per_source_delta(tmp_path: Path):
    baseline = tmp_path / "b.json"
    candidate = tmp_path / "c.json"
    baseline.write_text(
        json.dumps(
            {
                "rows": [
                    {"source": "a", "mean_quality": 0.4, "n_license_clean": 1, "n_records": 2},
                    {
                        "source": "__total__",
                        "mean_quality": 0.4,
                        "n_license_clean": 1,
                        "n_records": 2,
                    },
                ]
            }
        )
    )
    candidate.write_text(
        json.dumps(
            {
                "rows": [
                    {"source": "a", "mean_quality": 0.6, "n_license_clean": 2, "n_records": 2},
                    {
                        "source": "__total__",
                        "mean_quality": 0.6,
                        "n_license_clean": 2,
                        "n_records": 2,
                    },
                ]
            }
        )
    )
    out = tmp_path / "diff.json"
    rc = main(
        [
            "compare-diff",
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    by_src = {d["source"]: d for d in payload["deltas"]}
    assert abs(by_src["a"]["mean_quality_delta"] - 0.2) < 1e-9
    assert by_src["a"]["n_license_clean_delta"] == 1
    assert abs(by_src["__total__"]["mean_quality_delta"] - 0.2) < 1e-9


def test_cli_compare_rejects_unknown_domain(tmp_path: Path):
    """argparse choices should reject an unknown domain fast."""
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        main(
            [
                "compare",
                "--fixtures",
                "--domain",
                "nonexistent",
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
