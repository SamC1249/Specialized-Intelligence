"""Canonical data structures. See `db_structured.md` — single source of truth.

Every other module imports types from here. Do not redefine these locally.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


def _resolved_git_sha() -> str:
    """Return a short git SHA when we can, else ``"dev"``.

    CI sets ``SPECINT_GIT_SHA`` explicitly (see ``.github/workflows``).
    Local invocations fall back to ``git rev-parse --short HEAD``. If
    neither works, we return the literal string ``"dev"``. Never raises.
    """
    env = os.environ.get("SPECINT_GIT_SHA", "").strip()
    if env:
        return env[:12]
    try:  # pragma: no cover - environment-dependent
        import subprocess

        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(__file__) or ".",
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        )
        return out.decode().strip() or "dev"
    except Exception:  # pragma: no cover - environment-dependent
        return "dev"


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


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    extractor: str
    extractor_git: str = Field(default_factory=_resolved_git_sha)
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
            notes=notes,
        )


def utcnow() -> datetime:
    return datetime.now(UTC)


def serialize_records(records: list[VideoRecord]) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in records]
