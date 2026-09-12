"""Hard invariants for `VideoRecord` batches.

These are the guardrails that must hold for every batch of records
returned by any adapter, at any time. They are strict enough to raise
in library code and are exercised in tests as fixture-driven property
checks.

Invariants (numbered so failure messages carry the code):

  I1  Every record has non-empty `id` matching `f"{source}:{...}"`.
  I2  Every record has provenance with a non-empty `extractor`.
  I3  Every record's `license` value is a member of the `License` enum.
  I4  A record with a `RESTRICTED` or `UNKNOWN` license MUST NOT
      carry a `media_url` value. This is the load-bearing rule: if it
      ever fails we have leaked non-redistributable media into the
      corpus. All other invariants exist to defend it.
  I5  Within one batch, `VideoRecord.id` values are unique.
  I6  Every record's `source` matches its `id` prefix.

The `check_records` function returns a list of violations (empty on
success). The `assert_records` variant raises on the first violation
and is used inside tests and CLI safety gates.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from specint.records import License, VideoRecord

_NON_REDISTRIBUTABLE = {License.RESTRICTED, License.UNKNOWN}


@dataclass(frozen=True)
class InvariantViolation:
    code: str
    record_id: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.record_id}: {self.message}"


def _check_one(record: VideoRecord) -> list[InvariantViolation]:
    violations: list[InvariantViolation] = []
    rid = record.id or "<empty-id>"

    if not record.id or ":" not in record.id:
        violations.append(
            InvariantViolation(
                code="I1",
                record_id=rid,
                message="id must be non-empty and namespaced as '<source>:<native>'",
            )
        )

    if not record.provenance or not record.provenance.extractor:
        violations.append(
            InvariantViolation(
                code="I2",
                record_id=rid,
                message="provenance.extractor must be non-empty",
            )
        )

    if not isinstance(record.license, License):
        violations.append(
            InvariantViolation(
                code="I3",
                record_id=rid,
                message=f"license must be a License enum, got {type(record.license).__name__}",
            )
        )
    elif record.license in _NON_REDISTRIBUTABLE and record.media_url is not None:
        violations.append(
            InvariantViolation(
                code="I4",
                record_id=rid,
                message=(
                    f"non-redistributable license {record.license.value!r} "
                    "must not carry a media_url; adapters MUST null it out"
                ),
            )
        )

    if record.id and ":" in record.id:
        prefix = record.id.split(":", 1)[0]
        if prefix != record.source:
            violations.append(
                InvariantViolation(
                    code="I6",
                    record_id=rid,
                    message=(f"id prefix {prefix!r} does not match source {record.source!r}"),
                )
            )

    return violations


def check_records(records: Iterable[VideoRecord]) -> list[InvariantViolation]:
    items = list(records)
    violations: list[InvariantViolation] = []
    for rec in items:
        violations.extend(_check_one(rec))
    seen: dict[str, int] = {}
    for rec in items:
        seen[rec.id] = seen.get(rec.id, 0) + 1
    for rid, n in seen.items():
        if n > 1:
            violations.append(
                InvariantViolation(
                    code="I5",
                    record_id=rid,
                    message=f"duplicate id appears {n} times in the same batch",
                )
            )
    return violations


def assert_records(records: Sequence[VideoRecord]) -> None:
    violations = check_records(records)
    if not violations:
        return
    joined = "\n  - ".join(str(v) for v in violations)
    raise AssertionError(f"{len(violations)} invariant violation(s):\n  - {joined}")


def summarize(violations: Iterable[InvariantViolation]) -> dict[str, Any]:
    by_code: dict[str, int] = {}
    for v in violations:
        by_code[v.code] = by_code.get(v.code, 0) + 1
    return {"n_violations": sum(by_code.values()), "by_code": by_code}
