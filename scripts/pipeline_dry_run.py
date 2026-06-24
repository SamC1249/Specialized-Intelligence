#!/usr/bin/env python3
"""End-to-end dry run of the v0 pipeline against checked-in fixtures.

Stages:

  parse → score → contamination.filter → compare

For each registered source, load its fixture, run the adapter's
``parse``, attach quality scores, drop any records that match the
contamination blocklist, and write a deterministic JSONL manifest to
``data/manifests/dry-run-<date>.jsonl`` plus a comparison report to
``reports/dry-run-<date>.json``.

The script is the e2e backbone of ``tests/test_e2e_pipeline.py``: it
must be byte-for-byte deterministic across two consecutive runs so that
regressions in scoring / parsing / serialisation get caught
immediately, not at training time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from specint.compare import run_comparison
from specint.contamination import Blocklist, filter_contaminated
from specint.fixtures import parse_fixtures
from specint.quality import score_records
from specint.records import Provenance, SourceQuery, VideoRecord, serialize_records

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURES = REPO_ROOT / "tests" / "fixtures"

# Pin provenance time + git sha to deterministic values so dry-run output is
# byte-stable across consecutive runs (a precondition for CI-asserted
# regression detection — see ``tests/test_e2e_pipeline.py``).
DETERMINISTIC_FETCHED_AT = datetime(2026, 1, 1, tzinfo=UTC)
DETERMINISTIC_GIT = "dry-run"


def _canonicalise_provenance(record: VideoRecord) -> VideoRecord:
    canonical = Provenance(
        extractor=record.provenance.extractor,
        extractor_git=DETERMINISTIC_GIT,
        fetched_at=DETERMINISTIC_FETCHED_AT,
        query=record.provenance.query,
    )
    return record.model_copy(update={"provenance": canonical})


def _serialize_manifest(by_source: dict[str, list[VideoRecord]]) -> str:
    """Stable, deterministic JSONL serialisation of every kept record."""
    rows: list[VideoRecord] = []
    for slug in sorted(by_source):
        rows.extend(sorted(by_source[slug], key=lambda r: r.id))
    payload = serialize_records([_canonicalise_provenance(r) for r in rows])
    return "\n".join(json.dumps(p, sort_keys=True) for p in payload) + "\n"


def dry_run(
    fixtures_dir: Path = DEFAULT_FIXTURES,
    blocklist_path: Path | None = None,
    manifest_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, str]:
    """Run the dry-run pipeline; return ``{manifest_sha256, report_sha256}``."""
    query = SourceQuery(terms=["cooking", "recipe"], max_results=25)
    parsed = parse_fixtures(query, fixtures_dir=fixtures_dir)
    scored = {slug: score_records(records) for slug, records in parsed.items()}

    if blocklist_path is not None:
        blocklist = Blocklist.load(blocklist_path)
        kept: dict[str, list[VideoRecord]] = {}
        dropped_total = 0
        for slug, records in scored.items():
            k, d = filter_contaminated(records, blocklist)
            kept[slug] = k
            dropped_total += len(d)
        scored = kept
    else:
        dropped_total = 0

    manifest_text = _serialize_manifest(scored)
    rows = run_comparison(query, scored, notes="dry-run")
    report_payload = {
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
        "contamination_dropped": dropped_total,
    }
    report_text = json.dumps(report_payload, indent=2, sort_keys=True) + "\n"

    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(manifest_text)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text)

    return {
        "manifest_sha256": hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
        "report_sha256": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        "n_records": str(sum(len(v) for v in scored.values())),
        "n_dropped": str(dropped_total),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pipeline_dry_run")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--blocklist", default=None)
    parser.add_argument(
        "--manifest",
        default=str(REPO_ROOT / "data" / "manifests" / f"dry-run-{date.today().isoformat()}.jsonl"),
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / f"dry-run-{date.today().isoformat()}.json"),
    )
    args = parser.parse_args(argv)

    summary = dry_run(
        fixtures_dir=Path(args.fixtures),
        blocklist_path=Path(args.blocklist) if args.blocklist else None,
        manifest_path=Path(args.manifest),
        report_path=Path(args.report),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
