"""Canonical data structures. See `db_structured.md` — single source of truth.

Every other module imports types from here. Do not redefine these locally.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from specint.compliance import RightsSignal
from specint.gitmeta import short_sha


class License(str, Enum):  # - keep classic str+Enum for Pydantic compatibility
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
    extractor_git: str = "dev"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    query: str = ""
    raw_sha256: str = ""
    rights: RightsSignal | None = None


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
    aspect_ratio: float | None = None
    audio_present: bool | None = None
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


def make_provenance(
    extractor: str,
    query: str,
    raw: Any = None,
    rights: RightsSignal | None = None,
) -> Provenance:
    """Factory that fills in `extractor_git` and `raw_sha256` consistently."""
    return Provenance(
        extractor=extractor,
        extractor_git=short_sha(),
        fetched_at=utcnow(),
        query=query,
        raw_sha256=sha256_of_raw(raw) if raw is not None else "",
        rights=rights,
    )


def sha256_of_raw(raw: Any) -> str:
    """Content-addressed hash of a raw upstream payload.

    Accepts str (used as-is), bytes (used as-is), or any JSON-serializable
    value (serialised deterministically). Callers must feed the *exact*
    bytes/text they received from the upstream so replays are auditable.
    """
    if isinstance(raw, bytes):
        return hashlib.sha256(raw).hexdigest()
    if isinstance(raw, str):
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
