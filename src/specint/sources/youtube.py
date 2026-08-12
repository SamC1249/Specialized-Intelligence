"""YouTube Data API adapter — strictly `videoLicense=creativeCommon`.

Per `AGENTS.md` the only permitted use of YouTube is discovery of
Creative-Commons-licensed videos via the public Data API v3. We consume
URLs + metadata only — `media_url` is intentionally *never* populated
because YouTube's ToS forbid bulk redistribution of the media itself,
regardless of the video-level license the uploader selected.

Two calls compose one search:
  1. `search.list?part=snippet&videoLicense=creativeCommon&type=video&q=...`
     yields a page of `videoId`s + snippet fields.
  2. `videos.list?part=snippet,contentDetails,status&id=...` returns
     duration (ISO-8601), definition (`hd`/`sd`), and `license` (must
     equal `creativeCommon`; we defensively re-check).

`search()` requires `YOUTUBE_API_KEY` in the environment. When absent it
returns an empty list so CI never hits the network. The `parse()`
helpers are pure and fixture-tested.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource
from specint.sources.common_crawl import parse_iso8601_duration

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _definition_to_height(definition: str | None) -> int | None:
    if not definition:
        return None
    if definition.lower() == "hd":
        return 720
    if definition.lower() == "sd":
        return 480
    return None


def parse_video_list(raw: dict[str, Any], query: SourceQuery) -> list[VideoRecord]:
    """Pure parser for a `videos.list` response payload."""

    items = raw.get("items") or []
    prov = Provenance(
        extractor=__name__,
        fetched_at=utcnow(),
        query=query.serialize(),
    )
    out: list[VideoRecord] = []
    for item in items:
        video_id = item.get("id")
        if not isinstance(video_id, str) or not video_id:
            continue
        status = item.get("status") or {}
        if status.get("license") != "creativeCommon":
            continue

        snippet = item.get("snippet") or {}
        content = item.get("contentDetails") or {}
        title = str(snippet.get("title") or "")
        description = str(snippet.get("description") or "")
        channel = snippet.get("channelTitle")
        published = _parse_iso(snippet.get("publishedAt"))
        tags = snippet.get("tags") or []
        default_lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")

        duration_s = parse_iso8601_duration(content.get("duration"))
        height = _definition_to_height(content.get("definition"))

        record = VideoRecord(
            id=f"youtube:{video_id}",
            source="youtube",
            source_native_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            media_url=None,  # ToS: never distribute the media.
            title=title,
            description=description,
            language=default_lang if isinstance(default_lang, str) else None,
            duration_s=duration_s,
            width=None,
            height=height,
            fps=None,
            license=License.CC_BY,
            license_url="https://creativecommons.org/licenses/by/3.0/",
            author=channel if isinstance(channel, str) else None,
            published_at=published,
            keywords=[str(t) for t in tags if isinstance(t, str)],
            recipe_steps=[],
            provenance=prov,
        )
        out.append(record)
    return out


class YouTubeCCSource(BaseSource):
    slug = "youtube"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        return parse_video_list(raw, query)

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return []
        search_params: dict[str, str] = {
            "part": "snippet",
            "type": "video",
            "videoLicense": "creativeCommon",
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 50)),
            "key": api_key,
        }
        if query.language:
            search_params["relevanceLanguage"] = query.language

        resp = self.client().get(SEARCH_URL, params=search_params)
        resp.raise_for_status()
        ids = [
            item["id"]["videoId"]
            for item in (resp.json().get("items") or [])
            if isinstance(item, dict)
            and isinstance(item.get("id"), dict)
            and item["id"].get("videoId")
        ]
        if not ids:
            return []
        videos_params = {
            "part": "snippet,contentDetails,status",
            "id": ",".join(ids),
            "key": api_key,
        }
        vresp = self.client().get(VIDEOS_URL, params=videos_params)
        vresp.raise_for_status()
        return self.parse(vresp.json(), query)
