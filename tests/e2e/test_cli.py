"""End-to-end: the ``si`` CLI smoke tests.

We don't bother spawning a subprocess for these; ``typer.testing.CliRunner``
is enough and runs in-process.
"""

from __future__ import annotations

from typer.testing import CliRunner

from specialized_intelligence.cli import app

runner = CliRunner()


def test_version_command() -> None:
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert res.stdout.strip()


def test_stages_lists_known_stages() -> None:
    res = runner.invoke(app, ["stages"])
    assert res.exit_code == 0
    # These names match `db_structured.md` section 2.
    for needle in ["discover", "acquire", "curate.clip", "annotate.caption"]:
        assert needle in res.stdout


def test_licenses_table_contains_every_norm() -> None:
    res = runner.invoke(app, ["licenses"])
    assert res.exit_code == 0
    for needle in ["CC0", "CC_BY", "CC_BY_SA", "UNKNOWN"]:
        assert needle in res.stdout
