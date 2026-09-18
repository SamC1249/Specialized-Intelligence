"""YouTube Data API v3 Creative-Commons-only listing adapter.

**Legal scope.** We use YouTube's public Data API v3 *only* to list videos
whose uploader declared ``videoLicense=creativeCommon`` (which per the
YouTube ToS is CC-BY 3.0). We store URL + metadata. We do **not**
download media through this adapter, and we do not scrape the site HTML.

The adapter is metadata-only by design:
  * search: ``search.list?type=video&videoLicense=creativeCommon``
  * enrichment: ``videos.list?part=contentDetails,statistics,status``

Live calls require both ``SPECINT_RUN_INTEGRATION=1`` and
``YOUTUBE_API_KEY``. Otherwise the offline ``parse()`` is used
against a checked-in fixture.

Because uploaders can lie about "creativeCommon" (and can later revoke),
we default to :attr:`License.CC_BY` **only when** the ``status.license``
field of the ``videos.list`` response confirms it. Anything else is
demoted to :attr:`License.UNKNOWN` so it cannot enter a training set.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.quality.licenses import classify
from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


_DURATION_RE = None


def _parse_iso_duration(value: str | None) -> float | None:
    global _DURATION_RE
    if not value:
        return None
    import re

    if _DURATION_RE is None:
        _DURATION_RE = re.compile(r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$")
    m = _DURATION_RE.match(value.strip())
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return float(parts["h"] * 3600 + parts["m"] * 60 + parts["s"])


class YouTubeCreativeCommonsSource(BaseSource):
    """Metadata-only YouTube adapter, restricted to CC-BY-licensed uploads."""

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
            video_id = _resolve_video_id(item)
            if not video_id:
                continue
            snippet = item.get("snippet") or {}
            content_details = item.get("contentDetails") or {}
            status = item.get("status") or {}
            declared = (status.get("license") or "").lower()
            license_enum = License.CC_BY if declared == "creativecommon" else classify(declared)

            url = f"https://www.youtube.com/watch?v={video_id}"
            record = VideoRecord(
                id=f"youtube_cc:{video_id}",
                source="youtube_cc",
                source_native_id=video_id,
                url=url,
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                duration_s=_parse_iso_duration(content_details.get("duration")),
                width=None,
                height=None,
                fps=None,
                license=license_enum,
                license_url=("https://creativecommons.org/licenses/by/3.0/")
                if license_enum is License.CC_BY
                else None,
                author=snippet.get("channelTitle"),
                published_at=_iso(snippet.get("publishedAt")),
                keywords=list(snippet.get("tags") or []),
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
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 50)),
            "key": api_key,
        }
        if query.language:
            params["relevanceLanguage"] = query.language
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        search_payload = resp.json()
        video_ids = [
            item.get("id", {}).get("videoId")
            for item in search_payload.get("items", [])
            if item.get("id", {}).get("videoId")
        ]
        if not video_ids:
            return []
        detail = self.client().get(
            VIDEOS_URL,
            params={
                "part": "snippet,contentDetails,status",
                "id": ",".join(video_ids),
                "key": api_key,
            },
        )
        detail.raise_for_status()
        return self.parse(detail.json(), query)


def _resolve_video_id(item: dict[str, Any]) -> str | None:
    if isinstance(item.get("id"), str):
        return item["id"]
    if isinstance(item.get("id"), dict):
        return item["id"].get("videoId")
    return None
