"""New CLI paths: --scorer, --head-to-head, yield, languages."""

from __future__ import annotations

import json
from pathlib import Path

from specint.cli import main


def test_cli_languages(capsys):
    assert main(["languages"]) == 0
    out = capsys.readouterr().out.split()
    for lang in ("en", "es", "fr", "ja"):
        assert lang in out


def test_cli_compare_scorer_v2_produces_scorer_field(tmp_path: Path, capsys):
    out = tmp_path / "r.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "--scorer",
            "v2",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["scorer"] == "v2"


def test_cli_compare_head_to_head_emits_both(tmp_path: Path, capsys):
    out = tmp_path / "h2h.json"
    rc = main(["compare", "--fixtures", "--head-to-head", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert set(payload["scorers"]) == {"v1", "v2"}


def test_cli_yield_offline_writes_estimates(tmp_path: Path, capsys):
    out = tmp_path / "y.json"
    rc = main(
        [
            "yield",
            "--fixtures-dir",
            "tests/fixtures",
            "--terms",
            "cooking",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    sources = {e["source"] for e in payload["estimates"]}
    assert {"wikimedia", "archive_org", "peertube", "youtube"} <= sources
    yt = next(e for e in payload["estimates"] if e["source"] == "youtube")
    assert yt["est_hours_redistributable"] == 0.0


def test_cli_yield_requires_fixtures_dir(capsys):
    assert main(["yield"]) == 2


def test_cli_compare_language_flag_serialises_into_query(tmp_path: Path):
    out = tmp_path / "r.json"
    assert (
        main(
            [
                "compare",
                "--fixtures",
                "--terms",
                "cooking",
                "--languages",
                "fr",
                "es",
                "--output",
                str(out),
            ]
        )
        == 0
    )
    payload = json.loads(out.read_text())
    assert payload["query"]["languages"] == ["fr", "es"]
