"""YouTube Data API v3 adapter — Creative Commons listings only.

This adapter is *URL + metadata only*. We never download media from
YouTube. We only harvest listings where the uploader has explicitly
declared `videoLicense=creativeCommon`, which YouTube documents as
CC-BY. That's inside the `AGENTS.md` allowlist:

    > YouTube Data API only for `videoLicense=creativeCommon` listings
    > (URL + metadata, no media download)

`search(query)` requires the `YOUTUBE_API_KEY` env var. When it is
absent the adapter no-ops, so unit tests and the fixtures-mode CLI stay
completely offline.

`parse(raw)` handles both:
  1. The bare `search.list` response (`items[].id.videoId`,
     `items[].snippet.{title,description,channelTitle,publishedAt}`),
  2. A "fused" payload that also includes matched `videos.list` details
     (`items[].contentDetails.duration`, `items[].snippet.tags`).

We *always* stamp `License.CC_BY` because the API filter guarantees
that; we still record the license URL for downstream auditors.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.provenance_git import current_git_sha
from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_BASE = "https://www.googleapis.com/youtube/v3"
CC_BY_URL = "https://creativecommons.org/licenses/by/3.0/"

_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


def _parse_iso_duration(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None
    m = _ISO_DURATION_RE.match(value.strip())
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return float(
        parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
    )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _video_id(item: dict[str, Any]) -> str | None:
    id_field = item.get("id")
    if isinstance(id_field, dict):
        return id_field.get("videoId")
    if isinstance(id_field, str):
        return id_field
    return None


class YouTubeCCSource(BaseSource):
    slug = "youtube_cc"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        items = raw.get("items") or []
        prov = Provenance(
            extractor=__name__,
            extractor_git=current_git_sha(),
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for item in items:
            vid = _video_id(item)
            if not vid:
                continue
            snippet = item.get("snippet") or {}
            content = item.get("contentDetails") or {}
            duration_s = _parse_iso_duration(content.get("duration"))
            tags = snippet.get("tags")
            if not isinstance(tags, list):
                tags = []
            record = VideoRecord(
                id=f"youtube_cc:{vid}",
                source="youtube_cc",
                source_native_id=vid,
                url=f"https://www.youtube.com/watch?v={vid}",
                # AGENTS.md forbids media download for YouTube — leave None.
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                duration_s=duration_s,
                width=None,
                height=None,
                fps=None,
                license=License.CC_BY,
                license_url=CC_BY_URL,
                author=snippet.get("channelTitle"),
                published_at=_parse_iso(snippet.get("publishedAt")),
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
        resp = self.client().get(f"{API_BASE}/search", params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
