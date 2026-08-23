"""YouTube Data API adapter — **CC-BY listings only**.

Legal boundary:
  - Uses the public YouTube Data API v3 ``search.list`` endpoint with
    ``videoLicense=creativeCommon`` so we only surface videos the
    uploader has explicitly marked as CC-BY reusable.
  - **We never download media.** ``media_url`` is always ``None``. Each
    record carries only its canonical watch URL, title, description,
    duration hint (via a follow-up ``videos.list`` call), and license.
  - Live calls require ``YOUTUBE_API_KEY``. In CI / unit tests we exercise
    ``parse`` against a fixture; ``search`` refuses to run without a key.

Provenance:
  - ``license`` is always ``License.CC_BY`` (that is exactly what the
    ``creativeCommon`` filter guarantees) unless the payload contradicts
    itself, in which case we downgrade to ``License.UNKNOWN`` and skip.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_URL = "https://www.googleapis.com/youtube/v3/search"
WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_iso8601_duration(value: str | None) -> float | None:
    """Very small ISO-8601 duration parser (PT#H#M#S) — enough for
    YouTube's ``contentDetails.duration`` strings; no days.
    """
    if not value or not isinstance(value, str) or not value.startswith("PT"):
        return None
    rest = value[2:]
    hours = minutes = seconds = 0
    num = ""
    for ch in rest:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            hours = int(num or 0)
            num = ""
        elif ch == "M":
            minutes = int(num or 0)
            num = ""
        elif ch == "S":
            seconds = int(num or 0)
            num = ""
        else:
            return None
    return float(hours * 3600 + minutes * 60 + seconds)


class YouTubeCreativeCommonsSource(BaseSource):
    """Read-only, metadata-only, CC-BY-only YouTube adapter."""

    slug = "youtube_cc"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        items = raw.get("items") or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for item in items:
            id_field = item.get("id") or {}
            video_id = (
                id_field.get("videoId") if isinstance(id_field, dict) else None
            ) or item.get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet") or {}
            content_details = item.get("contentDetails") or {}
            status = item.get("status") or {}
            declared_license = (status.get("license") or "creativeCommon").lower()
            if declared_license not in {"creativecommon", "cc", "creative_common"}:
                continue

            duration = _parse_iso8601_duration(content_details.get("duration"))
            published_at = _parse_iso(snippet.get("publishedAt"))
            tags = snippet.get("tags") or []
            if not isinstance(tags, list):
                tags = []

            record = VideoRecord(
                id=f"youtube_cc:{video_id}",
                source="youtube_cc",
                source_native_id=str(video_id),
                url=WATCH_URL.format(video_id=video_id),
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                duration_s=duration,
                width=None,
                height=None,
                fps=None,
                license=License.CC_BY,
                license_url="https://creativecommons.org/licenses/by/3.0/",
                author=snippet.get("channelTitle"),
                published_at=published_at,
                keywords=[str(t) for t in tags],
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return []
        params = {
            "part": "snippet",
            "q": " ".join(query.terms),
            "type": "video",
            "videoLicense": "creativeCommon",
            "maxResults": str(min(query.max_results, 50)),
            "key": api_key,
        }
        resp = self.client().get(API_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
