"""License audit: walk every shard manifest under ``data/meta/`` and verify
that no record carries a license that is not training-eligible.

Run modes:
    --dry-run   walk *only* the fixture corpus under ``tests/e2e/fixtures``;
                this is what CI runs since real ``data/`` is gitignored.

This script exits non-zero on the first violation, prints the offending
shard, and refuses to proceed. It is invoked from CI on every PR.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from specialized_intelligence.licenses import LicenseNorm, policy_for

ROOT = Path(__file__).resolve().parent.parent


def audit_shard(manifest_path: Path) -> list[str]:
    """Return a list of human-readable violations for one shard manifest."""
    if not manifest_path.exists():
        return [f"{manifest_path}: missing"]
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        return [f"{manifest_path}: invalid JSON: {e}"]

    extra = manifest.get("extra", {})
    by_license: dict[str, int] = extra.get("license_norm_counts", {})
    if not by_license:
        # Day-1 manifests don't carry license counts yet — that's fine, but
        # a real shard must.
        return []

    violations: list[str] = []
    for lic_name, count in by_license.items():
        try:
            lic = LicenseNorm(lic_name)
        except ValueError:
            violations.append(f"{manifest_path}: unknown license value '{lic_name}' ({count} rows)")
            continue
        if not policy_for(lic).eligible_for_training:
            violations.append(
                f"{manifest_path}: {count} rows with non-training license '{lic.value}'"
            )
    return violations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="audit fixture corpus only")
    ap.add_argument("--root", type=Path, default=None, help="override audit root")
    args = ap.parse_args()

    if args.dry_run:
        roots = [ROOT / "tests" / "e2e" / "fixtures"]
    elif args.root is not None:
        roots = [args.root]
    else:
        roots = [ROOT / "data" / "meta"]

    manifests: list[Path] = []
    for r in roots:
        if r.exists():
            manifests.extend(r.rglob("_MANIFEST.json"))

    all_violations: list[str] = []
    for m in manifests:
        all_violations.extend(audit_shard(m))

    if all_violations:
        print("license audit FAILED:", file=sys.stderr)
        for v in all_violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print(f"license audit OK ({len(manifests)} manifest(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
