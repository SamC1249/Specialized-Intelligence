"""YouTube Data API v3 adapter — **URL + metadata only**.

Per `AGENTS.md`, the YouTube Data API is on the legal allowlist strictly
for `videoLicense=creativeCommon` listings. **We never fetch or
redistribute media bytes** — `media_url` is always `None` — and the
downstream training pipeline is expected to use the URL as a pointer to
re-fetch on the user's own account under whatever license the video
carries at fetch time.

License classification: YouTube's Data API returns `snippet.license`
values of `youtube` (standard) or `creativeCommon`. Because we filter
the search request with `videoLicense=creativeCommon`, every record
this adapter yields is treated as `License.CC_BY` (YouTube's CC option
is CC-BY 3.0). Any record that returns a different license value is
downgraded to `License.UNKNOWN` defensively.

Offline testing: `parse(raw, query)` accepts the exact JSON structure
returned by `search.list?part=snippet` combined with `videos.list?part=
contentDetails,snippet,status` (both merged into one dict). Fixtures in
`tests/fixtures/youtube_cc/` demonstrate the schema.

Live search: requires `YOUTUBE_API_KEY`. Skipped in unit tests; only
runs when `SPECINT_RUN_INTEGRATION=1` **and** the env var is set.
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

_ISO_DUR_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def _parse_youtube_duration(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None
    m = _ISO_DUR_RE.match(value.strip())
    if not m:
        return None
    h, mnt, s = (int(g) if g else 0 for g in m.groups())
    total = h * 3600 + mnt * 60 + s
    return float(total) if total > 0 else None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _license_from_status(license_value: str | None) -> License:
    if license_value == "creativeCommon":
        return License.CC_BY
    return License.UNKNOWN


class YouTubeCCSource(BaseSource):
    """Metadata-only adapter for `videoLicense=creativeCommon` listings.

    Records emitted:
      - `url` = canonical YouTube watch URL
      - `media_url` = ``None`` **always** (constitutional constraint)
      - `license` = `CC_BY` when upstream confirmed, else `UNKNOWN`
      - `duration_s`, `title`, `description`, `author`, `keywords`,
        `published_at` populated from the API payload
      - `provenance.extractor` records module path + serialized query
    """

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
            vid = item.get("id")
            if isinstance(vid, dict):
                vid = vid.get("videoId")
            if not vid or not isinstance(vid, str):
                continue

            snippet = item.get("snippet") or {}
            status = item.get("status") or {}
            content = item.get("contentDetails") or {}

            license_enum = _license_from_status(status.get("license"))
            if status.get("uploadStatus") == "rejected":
                license_enum = License.UNKNOWN

            duration_s = _parse_youtube_duration(content.get("duration"))
            height: int | None = None
            width: int | None = None
            definition = (content.get("definition") or "").lower()
            if definition == "hd":
                height = 720

            title = str(snippet.get("title") or "")
            description = str(snippet.get("description") or "")
            author = snippet.get("channelTitle") or None
            language = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")
            keywords = list(snippet.get("tags") or [])
            published = _parse_iso(snippet.get("publishedAt"))

            record = VideoRecord(
                id=f"youtube_cc:{vid}",
                source="youtube_cc",
                source_native_id=vid,
                url=f"https://www.youtube.com/watch?v={vid}",
                media_url=None,
                title=title,
                description=description,
                language=language,
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=license_enum,
                license_url=(
                    "https://creativecommons.org/licenses/by/3.0/"
                    if license_enum is License.CC_BY
                    else None
                ),
                author=author,
                published_at=published,
                keywords=keywords,
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
        if query.language:
            params["relevanceLanguage"] = query.language
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        search_payload = resp.json()

        ids = []
        for item in search_payload.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if vid:
                ids.append(vid)
        if not ids:
            return []

        detail_resp = self.client().get(
            VIDEOS_URL,
            params={
                "part": "snippet,contentDetails,status",
                "id": ",".join(ids),
                "key": api_key,
            },
        )
        detail_resp.raise_for_status()
        return self.parse(detail_resp.json(), query)
