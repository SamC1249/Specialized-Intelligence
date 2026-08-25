"""YouTube Data API v3 — Creative Commons listings only, metadata only.

Contract (strict):

- We hit `search.list` with ``videoLicense=creativeCommon`` and no other
  license values. We then optionally verify each hit against
  `videos.list?part=contentDetails,status` because YouTube's search
  results are *self-reported* — `status.license` and
  `contentDetails.licensedContent` must both agree before we upgrade the
  license from `UNKNOWN` to `CC_BY`.
- `media_url` is **always** `None`. We never redistribute video bytes;
  the record's `url` is the watch page.
- Uses `YOUTUBE_API_KEY` from the environment for live calls; unit tests
  feed a JSON fixture directly into `parse()` and never touch the network.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, SourceQuery, VideoRecord, make_provenance
from specint.sources.base import BaseSource

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_iso8601_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso8601_pt_duration_seconds(value: str | None) -> float | None:
    if not value or not value.startswith("PT"):
        return None
    total = 0
    num = ""
    for ch in value[2:]:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            total += int(num or 0) * 3600
            num = ""
        elif ch == "M":
            total += int(num or 0) * 60
            num = ""
        elif ch == "S":
            total += int(num or 0)
            num = ""
        else:
            return None
    return float(total)


class YouTubeCreativeCommonsSource(BaseSource):
    """CC-licensed YouTube listings (metadata only, no downloads)."""

    slug = "youtube_cc"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        prov = make_provenance(extractor=__name__, query=query.serialize(), raw=raw)
        details_by_id: dict[str, dict[str, Any]] = {}
        for entry in raw.get("videos", []) or []:
            if not isinstance(entry, dict):
                continue
            vid = entry.get("id")
            if isinstance(vid, str):
                details_by_id[vid] = entry

        out: list[VideoRecord] = []
        for item in raw.get("items", []) or []:
            snippet = item.get("snippet") or {}
            id_block = item.get("id") or {}
            vid = id_block.get("videoId") if isinstance(id_block, dict) else id_block
            if not isinstance(vid, str) or not vid:
                continue

            details = details_by_id.get(vid)
            declared_license = License.UNKNOWN
            license_url = None
            duration_s: float | None = None
            width = height = None
            if details:
                status = details.get("status") or {}
                content = details.get("contentDetails") or {}
                declared = str(status.get("license") or "").lower()
                licensed_content = bool(content.get("licensedContent", False))
                # Guard against contradictory declarations (see plan risk #3).
                if declared == "creativecommon" and not licensed_content:
                    declared_license = License.CC_BY
                    license_url = "https://creativecommons.org/licenses/by/3.0/"
                elif declared == "creativecommon" and licensed_content:
                    declared_license = License.UNKNOWN
                duration_s = _iso8601_pt_duration_seconds(content.get("duration"))
                dims = content.get("dimension")
                if dims and isinstance(details.get("player"), dict):
                    pass  # `player.embedHtml` is not reliable for dimensions.

            record = VideoRecord(
                id=f"youtube_cc:{vid}",
                source="youtube_cc",
                source_native_id=vid,
                url=f"https://www.youtube.com/watch?v={vid}",
                media_url=None,
                title=str(snippet.get("title") or vid),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=declared_license,
                license_url=license_url,
                author=snippet.get("channelTitle") or snippet.get("channelId"),
                published_at=_parse_iso8601_datetime(snippet.get("publishedAt")),
                keywords=[t for t in (snippet.get("tags") or []) if isinstance(t, str)],
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
            "type": "video",
            "videoLicense": "creativeCommon",
            "maxResults": str(min(query.max_results, 50)),
            "q": " ".join(query.terms),
            "key": api_key,
        }
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        search_data = resp.json()
        ids = [
            (item.get("id") or {}).get("videoId")
            for item in search_data.get("items", []) or []
            if isinstance(item.get("id"), dict)
        ]
        ids = [i for i in ids if i]
        videos_data: dict[str, Any] = {"items": []}
        if ids:
            v_params = {
                "part": "contentDetails,status,snippet",
                "id": ",".join(ids),
                "key": api_key,
            }
            v_resp = self.client().get(VIDEOS_URL, params=v_params)
            v_resp.raise_for_status()
            videos_data = v_resp.json()
        merged = {
            **search_data,
            "videos": [
                {
                    "id": v.get("id"),
                    "status": v.get("status"),
                    "contentDetails": v.get("contentDetails"),
                    "snippet": v.get("snippet"),
                }
                for v in videos_data.get("items", []) or []
            ],
        }
        return self.parse(merged, query)
