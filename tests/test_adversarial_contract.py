"""Adversarial contract tests.

These tests enforce the *operating contract* in `AGENTS.md`, not any
one adapter. They are deliberately "adversarial" in the sense that
they fail when the repo's own self-discipline slips:

- Plan files must be named `docs/plan-YYYY-MM-DD.md` and dated.
- Every `docs/plan-*.md` must contain the required sections.
- Every artifact file referenced from the latest plan must exist.
- Every file under `reports/baseline-*.json` must be a valid
  `BenchmarkResult`-shaped payload.
- `plan.md` must contain a dated agent-identity line per existing
  daily plan.
- Every source adapter under `src/specint/sources/` (except
  `base.py` / `__init__.py`) must be registered in
  `specint.sources.REGISTRY`.

These are cheap, offline, and don't depend on fixtures growing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from specint.records import BenchmarkResult
from specint.sources import REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
REPORTS = REPO_ROOT / "reports"
SOURCES_DIR = REPO_ROOT / "src" / "specint" / "sources"

PLAN_NAME_RE = re.compile(r"^plan-(\d{4})-(\d{2})-(\d{2})\.md$")
PLAN_LINE_RE = re.compile(
    r"^- \[(Adversarial-Agent|Coding-Agent|Reviewer-Agent) @ "
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] ",
    re.MULTILINE,
)


def _plans() -> list[Path]:
    return sorted(DOCS.glob("plan-*.md"))


def _latest_plan() -> Path:
    plans = _plans()
    assert plans, "no docs/plan-YYYY-MM-DD.md files present"
    return plans[-1]


def test_at_least_one_plan_exists():
    assert _plans(), "repo must have at least one docs/plan-YYYY-MM-DD.md"


@pytest.mark.parametrize("plan", _plans(), ids=lambda p: p.name)
def test_plan_filename_is_dated(plan: Path):
    assert PLAN_NAME_RE.match(plan.name), f"{plan.name} must be named plan-YYYY-MM-DD.md"


@pytest.mark.parametrize("plan", _plans(), ids=lambda p: p.name)
def test_plan_has_required_sections(plan: Path):
    text = plan.read_text()
    required = ["Hypothes", "Deliverables" if "Deliverables" in text else "Concrete deliverables"]
    for marker in required:
        assert marker.lower() in text.lower(), f"{plan.name} missing section matching: {marker!r}"


def test_latest_plan_artifact_links_resolve():
    """Every ./artifacts/... or docs/artifacts/... markdown path cited in
    the latest plan must exist on disk. This catches broken follow-ups
    the day they're introduced."""
    plan = _latest_plan()
    text = plan.read_text()
    rel_refs = set(re.findall(r"`(docs/artifacts/[^`]+\.md)`", text))
    rel_refs |= set(re.findall(r"`(artifacts/[^`]+\.md)`", text))
    rel_refs |= {f"docs/{m}" for m in re.findall(r"\(\./artifacts/([^)]+\.md)\)", text)}
    for ref in sorted(rel_refs):
        candidate = REPO_ROOT / ref
        assert candidate.exists(), f"{plan.name} references missing artifact {ref}"


def test_plan_md_has_one_line_per_dated_plan():
    """`plan.md` is the daily log. Every `docs/plan-YYYY-MM-DD.md` must
    have at least one dated line in `plan.md` by one of the known
    agents on that same date (±1 day for timezone slack)."""
    log = (REPO_ROOT / "plan.md").read_text()
    dated_lines = {m.group(2)[:10] for m in PLAN_LINE_RE.finditer(log) if m.group(2)}
    for plan in _plans():
        m = PLAN_NAME_RE.match(plan.name)
        assert m is not None
        plan_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        assert plan_date in dated_lines, (
            f"plan.md missing a dated entry for {plan_date} ({plan.name})"
        )


@pytest.mark.parametrize("baseline", sorted(REPORTS.glob("baseline-*.json")), ids=lambda p: p.name)
def test_baseline_json_matches_schema(baseline: Path):
    payload = json.loads(baseline.read_text())
    assert "rows" in payload and isinstance(payload["rows"], list), (
        f"{baseline.name} must be an object with a 'rows' list"
    )
    sources_seen = set()
    for row in payload["rows"]:
        parsed = BenchmarkResult.model_validate(row)
        sources_seen.add(parsed.source)
        assert parsed.n_license_clean <= parsed.n_records, (
            f"{baseline.name}: {parsed.source} has n_license_clean > n_records"
        )
    assert "__total__" in sources_seen, f"{baseline.name} missing the aggregate __total__ row"


def test_every_source_module_is_registered():
    """Each adapter file under src/specint/sources/ (except base and
    __init__) must contribute a REGISTRY entry whose module path
    matches the file. Prevents stealth-adding a source without
    hooking it into the harness."""
    expected_modules = set()
    for py in SOURCES_DIR.glob("*.py"):
        if py.name in {"__init__.py", "base.py"}:
            continue
        expected_modules.add(f"specint.sources.{py.stem}")
    registered_modules = {cls.__module__ for cls in REGISTRY.values()}
    missing = expected_modules - registered_modules
    assert not missing, f"adapter files not registered in REGISTRY: {sorted(missing)}"


def test_latest_plan_cites_a_hypothesis_label():
    """The adversarial contract says plans state explicit hypotheses.
    We require at least one `H<number>` style label in the latest
    plan so hypotheses are addressable from code reviews."""
    text = _latest_plan().read_text()
    assert re.search(r"\bH\d+\b", text), "latest plan must label at least one hypothesis (e.g. H2)"
