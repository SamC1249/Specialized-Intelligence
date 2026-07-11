"""YouTube Data API v3 adapter — Creative-Commons-only, metadata only.

Legal contract (AGENTS.md allowlist):
  * We call `search.list` with `videoLicense=creativeCommon` so
    YouTube filters server-side; we then hit `videos.list` for the
    ids to get durations, sizes, and metadata.
  * We NEVER emit ``media_url``. YouTube's ToS forbid redistributing
    the media stream; the record is a URL + provenance pointer.
  * If any record's licence is not ``creativeCommon`` we downgrade it
    to ``License.RESTRICTED`` even though YouTube already filters.
    Defense in depth beats a Google API bug.

Offline path:
  ``parse`` is fixture-testable — pass a dict shaped like the merged
  ``search+videos`` payload (see ``tests/fixtures/youtube/``).

Live path:
  Requires ``SPECINT_YOUTUBE_API_KEY``. Search endpoint returns video
  IDs; a second call to ``videos.list?part=contentDetails,snippet,status``
  fills in durations and status. Both are documented public endpoints.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_iso_duration(value: str | None) -> float | None:
    if not value:
        return None
    m = _ISO_DURATION_RE.match(value.strip())
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return float(
        parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
    )


class YouTubeCCSource(BaseSource):
    """Metadata-only YouTube adapter.

    Only records with ``status.license == 'creativeCommon'`` are marked
    ``License.CC_BY``; everything else becomes ``License.RESTRICTED``.
    ``media_url`` is *always* None — even for CC records — because we
    are not allowed to redistribute YouTube's actual video streams.
    """

    slug = "youtube"

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
            video_id = item.get("id")
            if isinstance(video_id, dict):
                video_id = video_id.get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet") or {}
            status = item.get("status") or {}
            content = item.get("contentDetails") or {}

            declared_license = status.get("license", "").lower()
            license_enum = (
                License.CC_BY if declared_license == "creativecommon" else License.RESTRICTED
            )

            dims = content.get("dimension") or ""
            height: int | None = None
            width: int | None = None
            definition = (content.get("definition") or "").lower()
            if definition == "hd":
                height, width = 720, 1280
            elif definition == "sd":
                height, width = 480, 854
            if isinstance(content.get("height"), int):
                height = content["height"]
            if isinstance(content.get("width"), int):
                width = content["width"]

            record = VideoRecord(
                id=f"youtube:{video_id}",
                source="youtube",
                source_native_id=str(video_id),
                url=f"https://www.youtube.com/watch?v={video_id}",
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultLanguage")
                or snippet.get("defaultAudioLanguage")
                or None,
                duration_s=_parse_iso_duration(content.get("duration")),
                width=width,
                height=height,
                fps=None,
                license=license_enum,
                license_url=(
                    "https://creativecommons.org/licenses/by/3.0/"
                    if license_enum is License.CC_BY
                    else None
                ),
                author=str(snippet.get("channelTitle") or "") or None,
                published_at=_parse_iso(snippet.get("publishedAt")),
                keywords=list(snippet.get("tags") or []),
                recipe_steps=[],
                provenance=prov,
            )
            if dims:
                pass  # dimension is 2d/3d; we don't have a schema field for it yet.
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("SPECINT_YOUTUBE_API_KEY")
        if not api_key:
            return []
        client = self.client()
        search_params = {
            "part": "id",
            "type": "video",
            "videoLicense": "creativeCommon",
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 50)),
            "key": api_key,
        }
        if query.effective_languages:
            search_params["relevanceLanguage"] = query.effective_languages[0]
        search_resp = client.get(SEARCH_URL, params=search_params)
        search_resp.raise_for_status()
        ids = [
            (item.get("id") or {}).get("videoId")
            for item in (search_resp.json().get("items") or [])
        ]
        ids = [i for i in ids if i]
        if not ids:
            return []

        videos_params = {
            "part": "snippet,contentDetails,status",
            "id": ",".join(ids),
            "key": api_key,
        }
        videos_resp = client.get(VIDEOS_URL, params=videos_params)
        videos_resp.raise_for_status()
        return self.parse(videos_resp.json(), query)
