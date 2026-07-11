"""Canonical data structures. See `db_structured.md` — single source of truth.

Every other module imports types from here. Do not redefine these locally.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class License(str, Enum):  # noqa: UP042 - keep classic str+Enum for Pydantic compatibility
    CC0 = "CC0"
    CC_BY = "CC-BY"
    CC_BY_SA = "CC-BY-SA"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    OTHER_FREE = "OTHER_FREE"
    UNKNOWN = "UNKNOWN"
    RESTRICTED = "RESTRICTED"

    @property
    def is_redistributable(self) -> bool:
        return self in {
            License.CC0,
            License.CC_BY,
            License.CC_BY_SA,
            License.PUBLIC_DOMAIN,
            License.OTHER_FREE,
        }


@lru_cache(maxsize=1)
def extractor_git_sha() -> str:
    """Return the short SHA of the extractor repository, or ``"dev"``.

    Result is cached for the process lifetime. We look up the SHA once at
    first call to keep every ``Provenance`` reproducibly stamped without
    forking ``git`` per record.

    Precedence:
      1. Environment variable ``SPECINT_EXTRACTOR_GIT`` — used by
         reproducibility-critical CI runs.
      2. ``git rev-parse --short HEAD`` executed against the repo that
         contains this file.
      3. ``"dev"`` when no repo is available.
    """
    env = os.environ.get("SPECINT_EXTRACTOR_GIT")
    if env:
        return env.strip()[:12] or "dev"
    try:
        repo_dir = Path(__file__).resolve().parent
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_dir),
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        return "dev"
    return out.decode().strip() or "dev"


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    extractor: str
    extractor_git: str = Field(default_factory=extractor_git_sha)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    query: str = ""


class SourceQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    terms: list[str] = Field(default_factory=list)
    max_results: int = 50
    language: str | None = None

    def serialize(self) -> str:
        terms = "|".join(self.terms)
        return f"terms={terms};max={self.max_results};lang={self.language or ''}"


class VideoRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    source_native_id: str
    url: AnyHttpUrl
    media_url: AnyHttpUrl | None = None
    title: str
    description: str = ""
    language: str | None = None
    duration_s: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    license: License = License.UNKNOWN
    license_url: AnyHttpUrl | None = None
    author: str | None = None
    published_at: datetime | None = None
    keywords: list[str] = Field(default_factory=list)
    recipe_steps: list[str] = Field(default_factory=list)
    provenance: Provenance
    quality_score: float | None = None

    def with_quality(self, score: float) -> VideoRecord:
        return self.model_copy(update={"quality_score": score})


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    query_terms: list[str]
    n_records: int
    n_license_clean: int
    total_duration_s: float
    mean_quality: float
    p50_quality: float
    p90_quality: float
    unique_authors: int
    # Cross-source dedup metrics. Optional to keep the schema
    # backward-compatible for pre-2026-07-11 reports.
    n_unique_across_sources: int | None = None
    duplicate_rate: float | None = None
    unique_duration_s: float | None = None
    notes: str = ""

    @classmethod
    def empty(cls, source: str, query_terms: list[str], notes: str = "") -> BenchmarkResult:
        return cls(
            source=source,
            query_terms=list(query_terms),
            n_records=0,
            n_license_clean=0,
            total_duration_s=0.0,
            mean_quality=0.0,
            p50_quality=0.0,
            p90_quality=0.0,
            unique_authors=0,
            n_unique_across_sources=0,
            duplicate_rate=0.0,
            unique_duration_s=0.0,
            notes=notes,
        )


def utcnow() -> datetime:
    return datetime.now(UTC)


def serialize_records(records: list[VideoRecord]) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in records]
