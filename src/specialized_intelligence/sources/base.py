"""Common types for source adapters.

`DiscoveredVideo` mirrors the ``discovered_videos`` Parquet table defined
in `db_structured.md` section 2.1.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from specialized_intelligence.licenses import LicenseNorm, normalize_license


class DiscoveredVideo(BaseModel):
    """A single candidate video discovered from an upstream source.

    The schema is the authoritative Python representation of section 2.1
    of `db_structured.md`. Any change here requires the same change there.
    """

    video_uri: str = Field(..., description="canonical URI, e.g. 'youtube:dQw4w9WgXcQ'")
    source_id: str
    title: str
    duration_s: float | None = None
    upload_date: date | None = None
    license_tag: str
    license_norm: LicenseNorm
    channel_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime

    @classmethod
    def from_upstream(
        cls,
        *,
        video_uri: str,
        source_id: str,
        title: str,
        license_tag: str,
        discovered_at: datetime,
        duration_s: float | None = None,
        upload_date: date | None = None,
        channel_id: str | None = None,
        raw_metadata: dict[str, Any] | None = None,
    ) -> DiscoveredVideo:
        """Build a record while running license normalization centrally."""
        return cls(
            video_uri=video_uri,
            source_id=source_id,
            title=title,
            license_tag=license_tag,
            license_norm=normalize_license(license_tag),
            duration_s=duration_s,
            upload_date=upload_date,
            channel_id=channel_id,
            raw_metadata=raw_metadata or {},
            discovered_at=discovered_at,
        )


class SourceAdapter(Protocol):
    """Structural protocol for source-discovery adapters.

    Implementations live in ``sources/<source_id>.py``.
    """

    source_id: str

    def discover(self, *, query: str, max_results: int) -> list[DiscoveredVideo]:
        """Return up to ``max_results`` candidate videos for ``query``."""
        ...
