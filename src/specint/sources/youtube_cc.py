"""YouTube Data API v3 adapter — Creative-Commons listings only.

Per the project allowlist in `AGENTS.md`:

> YouTube Data API **only** for `videoLicense=creativeCommon` listings
> (URL + metadata, no media download)

Therefore this adapter:

- Always passes `videoLicense=creativeCommon` on `search.list`.
- Verifies the per-video `status.license == "creativeCommon"` on
  `videos.list` before emitting `License.CC_BY`. Any mismatch falls
  through to `License.UNKNOWN`, which downstream training filters
  reject.
- Never populates `media_url`. YouTube's own ToS forbids redistributing
  video bytes; we store only URL + metadata provenance.

`search()` requires both `SPECINT_RUN_INTEGRATION=1` *and*
`SPECINT_YOUTUBE_API_KEY=<...>`; CI never exercises it. `parse()` is a
pure function and is exercised by `tests/fixtures/youtube_cc/*.json`.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_iso8601_duration(value: str | None) -> float | None:
    if not value or not isinstance(value, str) or not value.startswith("PT"):
        return None
    hours = minutes = seconds = 0
    buf = ""
    for ch in value[2:]:
        if ch.isdigit():
            buf += ch
            continue
        if not buf:
            continue
        n = int(buf)
        buf = ""
        if ch == "H":
            hours = n
        elif ch == "M":
            minutes = n
        elif ch == "S":
            seconds = n
    total = hours * 3600 + minutes * 60 + seconds
    return float(total) if total > 0 else None


def _dimensions(definition: str | None) -> tuple[int | None, int | None]:
    if definition == "hd":
        return (1280, 720)
    if definition == "sd":
        return (640, 360)
    return (None, None)


class YouTubeCCSource(BaseSource):
    """Metadata-only YouTube adapter restricted to Creative-Commons listings."""

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
        for it in items:
            vid = (
                it.get("id")
                if isinstance(it.get("id"), str)
                else (it.get("id") or {}).get("videoId")
            )
            if not vid:
                continue
            snippet = it.get("snippet") or {}
            status = it.get("status") or {}
            content = it.get("contentDetails") or {}

            if status.get("license") != "creativeCommon":
                license_enum = License.UNKNOWN
            else:
                license_enum = License.CC_BY

            width, height = _dimensions(content.get("definition"))
            duration_s = _parse_iso8601_duration(content.get("duration"))

            record = VideoRecord(
                id=f"youtube_cc:{vid}",
                source="youtube_cc",
                source_native_id=str(vid),
                url=f"https://www.youtube.com/watch?v={vid}",
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage")
                or snippet.get("defaultLanguage")
                or None,
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
                author=snippet.get("channelTitle") or None,
                published_at=_parse_iso(snippet.get("publishedAt")),
                keywords=list(snippet.get("tags") or []),
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("SPECINT_YOUTUBE_API_KEY")
        if not api_key:
            return []
        search_params = {
            "part": "snippet",
            "type": "video",
            "videoLicense": "creativeCommon",
            "maxResults": str(min(query.max_results, 50)),
            "q": " ".join(query.terms),
            "key": api_key,
        }
        if query.language:
            search_params["relevanceLanguage"] = query.language

        resp = self.client().get(SEARCH_URL, params=search_params)
        resp.raise_for_status()
        search_payload = resp.json()

        ids = [
            (item.get("id") or {}).get("videoId")
            for item in (search_payload.get("items") or [])
            if (item.get("id") or {}).get("videoId")
        ]
        if not ids:
            return []

        videos_params = {
            "part": "snippet,contentDetails,status",
            "id": ",".join(ids),
            "key": api_key,
        }
        resp2 = self.client().get(VIDEOS_URL, params=videos_params)
        resp2.raise_for_status()
        return self.parse(resp2.json(), query)
