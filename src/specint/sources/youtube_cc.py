"""YouTube Data API v3 adapter — Creative Commons filter only.

Per AGENTS.md, the *only* permitted YouTube usage is the public
`youtube.videos.list`/`youtube.search.list` endpoints with
`videoLicense=creativeCommon`. We collect **URLs + metadata only**,
never media bytes.

`parse()` is pure and fixture-driven so tests remain fully offline.
`search()` requires `YOUTUBE_API_KEY` in the environment and is skipped
by the offline test suite.

Upstream field mapping (from `youtube.videos.list?part=snippet,contentDetails,statistics,status`):
  - `id`                                       -> `source_native_id`
  - `snippet.title`                            -> `title`
  - `snippet.description`                      -> `description`
  - `snippet.defaultAudioLanguage` / `snippet.defaultLanguage` -> `language`
  - `snippet.channelTitle`                     -> `author`
  - `snippet.publishedAt`                      -> `published_at`
  - `snippet.tags`                             -> `keywords`
  - `contentDetails.duration` (ISO8601)        -> `duration_s`
  - `contentDetails.definition` (`hd`/`sd`)    -> coarse height inference
  - `status.license` (`creativeCommon`|`youtube`) -> `License.CC_BY` or `RESTRICTED`

The `status.license` field is the single ground-truth signal for
redistribution. Anything that is not exactly `creativeCommon` is dropped
before it reaches the record list.
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
    d = definition.lower()
    if d == "hd":
        return 720
    if d == "sd":
        return 360
    return None


class YouTubeCCSource(BaseSource):
    """Only Creative-Commons-licensed YouTube videos, metadata only."""

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
            if not isinstance(item, dict):
                continue
            status = item.get("status") or {}
            if str(status.get("license", "")).lower() != "creativecommon":
                continue

            snippet = item.get("snippet") or {}
            content = item.get("contentDetails") or {}
            video_id = item.get("id")
            if isinstance(video_id, dict):
                video_id = video_id.get("videoId")
            if not video_id:
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            duration_s = parse_iso8601_duration(content.get("duration"))
            height = _definition_to_height(content.get("definition"))
            language = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")

            record = VideoRecord(
                id=f"youtube_cc:{video_id}",
                source="youtube_cc",
                source_native_id=str(video_id),
                url=url,
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=language if isinstance(language, str) else None,
                duration_s=duration_s,
                width=None,
                height=height,
                fps=None,
                license=License.CC_BY,
                license_url="https://creativecommons.org/licenses/by/3.0/",
                author=snippet.get("channelTitle")
                if isinstance(snippet.get("channelTitle"), str)
                else None,
                published_at=_parse_iso(snippet.get("publishedAt")),
                keywords=[str(t) for t in (snippet.get("tags") or []) if t],
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(
        self, query: SourceQuery
    ) -> Iterable[VideoRecord]:  # pragma: no cover - integration only
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return []
        params = {
            "part": "snippet",
            "type": "video",
            "videoLicense": "creativeCommon",
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 25)),
            "key": api_key,
        }
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        ids = [(item.get("id") or {}).get("videoId") for item in (resp.json().get("items") or [])]
        ids = [vid for vid in ids if vid]
        if not ids:
            return []
        details = self.client().get(
            VIDEOS_URL,
            params={
                "part": "snippet,contentDetails,status",
                "id": ",".join(ids),
                "key": api_key,
            },
        )
        details.raise_for_status()
        return self.parse(details.json(), query)
