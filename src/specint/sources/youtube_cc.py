"""YouTube Data API v3 adapter — Creative-Commons-only, metadata-only.

Per `AGENTS.md` allowlist: YouTube Data API is permitted for listings with
`videoLicense=creativeCommon`. We store URL + metadata only. We never
populate `media_url` and we never fetch any video bytes.

Live search requires a `SPECINT_YOUTUBE_API_KEY` environment variable and
`SPECINT_RUN_INTEGRATION=1`. Otherwise the adapter operates purely on
fixture JSON (parse-only), keeping CI hermetic.

Two upstream endpoints:
  - search.list: id + snippet
  - videos.list: contentDetails (duration ISO-8601) + status (license)

Our fixture inlines both under a single wrapper dict so `parse()` remains
pure and single-shot.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource
from specint.sources.common_crawl import parse_iso8601_duration

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

_ISO_LANG_RE = re.compile(r"^[a-zA-Z]{2,3}(?:-[A-Za-z0-9]+)?$")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _dimensions_from_thumbnails(thumbnails: Any) -> tuple[int | None, int | None]:
    if not isinstance(thumbnails, dict):
        return None, None
    best = None
    best_area = -1
    for meta in thumbnails.values():
        if not isinstance(meta, dict):
            continue
        w, h = meta.get("width"), meta.get("height")
        if isinstance(w, int) and isinstance(h, int) and w * h > best_area:
            best = (w, h)
            best_area = w * h
    return (best[0], best[1]) if best else (None, None)


class YouTubeCCSource(BaseSource):
    """YouTube-Data-API adapter restricted to `videoLicense=creativeCommon`."""

    slug = "youtube_cc"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        items = raw.get("items") or []
        details = {
            d.get("id"): d
            for d in (raw.get("videoDetails") or [])
            if isinstance(d, dict) and d.get("id")
        }
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            id_block = item.get("id") or {}
            video_id = id_block.get("videoId") if isinstance(id_block, dict) else id_block
            if not video_id:
                continue
            snippet = item.get("snippet") or {}
            detail = details.get(video_id, {})
            content = detail.get("contentDetails") or {}
            status = detail.get("status") or {}
            license_str = (status.get("license") or "").lower()
            if license_str and license_str not in {"creativecommon", "creative_common"}:
                continue

            duration_s = parse_iso8601_duration(content.get("duration"))
            width, height = _dimensions_from_thumbnails(snippet.get("thumbnails"))
            language = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")
            if isinstance(language, str) and not _ISO_LANG_RE.match(language):
                language = None

            record = VideoRecord(
                id=f"youtube_cc:{video_id}",
                source="youtube_cc",
                source_native_id=str(video_id),
                url=f"https://www.youtube.com/watch?v={video_id}",
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=language,
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=License.CC_BY,
                license_url="https://creativecommons.org/licenses/by/4.0/",
                author=str(snippet.get("channelTitle") or "") or None,
                published_at=_parse_iso(snippet.get("publishedAt")),
                keywords=list(snippet.get("tags") or []),
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:  # pragma: no cover
        api_key = os.environ.get("SPECINT_YOUTUBE_API_KEY")
        if not api_key or os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
            return []
        params = {
            "key": api_key,
            "part": "snippet",
            "type": "video",
            "videoLicense": "creativeCommon",
            "videoEmbeddable": "true",
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 50)),
        }
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()
        ids = [
            (item.get("id") or {}).get("videoId")
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        ids = [i for i in ids if i]
        if ids:
            det = self.client().get(
                VIDEOS_URL,
                params={
                    "key": api_key,
                    "part": "contentDetails,status",
                    "id": ",".join(ids),
                },
            )
            det.raise_for_status()
            payload["videoDetails"] = det.json().get("items", [])
        return self.parse(payload, query)
