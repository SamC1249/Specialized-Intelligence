"""Smoke test for `python -m specint compare --fixtures`.

The `--fixtures` CLI is what CI actually exercises. Today it produces
an all-zeros report because it never loads fixture data; the e2e test
loads fixtures directly and bypasses the CLI (H5 in
`docs/plan-2026-07-14.md`).

This test:

1. Asserts the CLI produces a valid, well-formed JSON report — always.
2. Asserts (via `xfail`) that the report has non-zero `n_records`.
   When Coding-Agent fixes H5, this xfail flips to xpass and the
   strict=True setting makes CI fail loudly until the marker is
   removed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specint.cli import main


def test_cli_compare_fixtures_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "recipe",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    payload = json.loads(out.read_text())
    assert "query" in payload and "rows" in payload
    assert payload["query"]["terms"] == ["cooking", "recipe"]
    slugs = {row["source"] for row in payload["rows"]}
    assert {"archive_org", "common_crawl", "peertube", "wikimedia", "__total__"} <= slugs


@pytest.mark.xfail(
    reason="H5 in plan-2026-07-14: CLI --fixtures currently emits zeros; Coding-Agent will fix.",
    strict=True,
)
def test_cli_compare_fixtures_is_not_all_zeros(tmp_path: Path) -> None:
    out = tmp_path / "compare.json"
    rc = main(
        [
            "compare",
            "--fixtures",
            "--terms",
            "cooking",
            "recipe",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    total = next(row for row in payload["rows"] if row["source"] == "__total__")
    assert total["n_records"] > 0, "CLI --fixtures produced all-zeros report"


def test_cli_sources_lists_all_registered_adapters(capsys) -> None:
    rc = main(["sources"])
    assert rc == 0
    captured = capsys.readouterr().out
    for slug in ("archive_org", "common_crawl", "peertube", "wikimedia"):
        assert slug in captured, f"CLI `sources` did not list {slug!r}"
