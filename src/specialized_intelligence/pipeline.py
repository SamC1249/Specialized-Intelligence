"""Pipeline contract.

Every stage in the curation DAG (see `db_structured.md` section 2)
implements `Stage`. Stages are idempotent on ``(record_id, stage_version)``,
read+write Parquet directories, and emit a ``_MANIFEST.json`` next to
their output that the CI uses to verify the contract.

The class is deliberately tiny: we want the contract enforced everywhere,
not a heavyweight framework.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class StageManifest:
    """Manifest emitted at the end of every stage run.

    The CI's ``audit_licenses.py`` reads these to walk the lineage of any
    output shard back to its sources.
    """

    stage_name: str
    stage_version: str
    git_sha: str
    started_at: str
    finished_at: str
    rows_in: int
    rows_out: int
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


class Stage(ABC):
    """Base class for a pipeline stage.

    Subclasses **must** set ``name`` and ``version`` class attributes and
    implement ``run``. ``version`` is bumped any time the output schema or
    semantics change; this is what makes pipeline runs reproducible.
    """

    name: str = ""
    version: str = ""

    def __init__(self, *, git_sha: str = "unknown") -> None:
        if not self.name:
            raise TypeError(f"{type(self).__name__} must set class attr `name`")
        if not self.version:
            raise TypeError(f"{type(self).__name__} must set class attr `version`")
        self.git_sha = git_sha

    @abstractmethod
    def run(self, input_dir: Path, output_dir: Path) -> StageManifest:
        """Run the stage from ``input_dir`` to ``output_dir``.

        Implementations must:

        * be idempotent on ``(record_id, version)``;
        * propagate the ``license_norm`` column verbatim from input to
          output for every record (the audit script enforces this);
        * write ``output_dir/_MANIFEST.json`` *atomically* at the end.

        Returns:
            the `StageManifest` written to disk.
        """

    def _write_manifest(
        self,
        output_dir: Path,
        *,
        started_at: datetime,
        rows_in: int,
        rows_out: int,
        extra: dict[str, Any] | None = None,
    ) -> StageManifest:
        manifest = StageManifest(
            stage_name=self.name,
            stage_version=self.version,
            git_sha=self.git_sha,
            started_at=started_at.replace(tzinfo=UTC).isoformat(),
            finished_at=datetime.now(tz=UTC).isoformat(),
            rows_in=rows_in,
            rows_out=rows_out,
            extra=extra or {},
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        tmp = output_dir / "_MANIFEST.json.tmp"
        final = output_dir / "_MANIFEST.json"
        tmp.write_text(manifest.to_json())
        tmp.replace(final)
        return manifest
