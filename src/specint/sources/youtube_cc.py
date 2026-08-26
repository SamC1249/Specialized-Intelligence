"""YouTube CC-BY-only adapter (metadata + landing URL only).

AGENTS.md rule #1 forbids scraping YouTube in general, but the same
section explicitly permits the YouTube Data API when it is filtered to
``videoLicense=creativeCommon`` — the only licence YouTube ever tags a
video with is CC-BY (v3.0). We store the landing URL plus metadata and
**never** the media URL, per AGENTS.md rule #1 ("URL provenance, not
bulk redistribution").

Live ``search()`` is gated on both ``YOUTUBE_API_KEY`` and
``SPECINT_RUN_INTEGRATION=1`` so unit tests never call out to YouTube.
The ``parse`` function operates on the raw JSON shape returned by:

    GET https://www.googleapis.com/youtube/v3/search
        ?type=video
        &videoLicense=creativeCommon
        &q=<terms>
        &part=snippet
        &maxResults=<n>

and, ideally, a follow-up ``videos.list`` call with
``part=contentDetails,status,snippet`` merged into each item under the
key ``contentDetails``. The parser tolerates both flat search-only
payloads and enriched merged payloads.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.licenses import classify
from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

_ISO_DUR = re.compile(r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$")


def _iso_duration(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None
    m = _ISO_DUR.match(value.strip())
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return float(parts["h"] * 3600 + parts["m"] * 60 + parts["s"])


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class YouTubeCCSource(BaseSource):
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
            vid = None
            id_field = item.get("id")
            if isinstance(id_field, dict):
                vid = id_field.get("videoId")
            elif isinstance(id_field, str):
                vid = id_field
            if not vid:
                continue

            snippet = item.get("snippet") or {}
            status = item.get("status") or {}
            details = item.get("contentDetails") or {}

            declared_license = (status.get("license") or "").strip().lower()
            if declared_license and declared_license != "creativecommon":
                continue
            license_enum = classify(
                "Creative Commons Attribution 3.0", "https://creativecommons.org/licenses/by/3.0/"
            )
            if license_enum is License.UNKNOWN:
                license_enum = License.CC_BY

            duration_s = _iso_duration(details.get("duration"))
            width = None
            height = None
            defn = (details.get("definition") or "").lower()
            if defn == "hd":
                height = 720
                width = 1280
            elif defn == "sd":
                height = 480
                width = 640

            keywords = snippet.get("tags") or []
            if not isinstance(keywords, list):
                keywords = []

            record = VideoRecord(
                id=f"youtube_cc:{vid}",
                source="youtube_cc",
                source_native_id=str(vid),
                url=f"https://www.youtube.com/watch?v={vid}",
                media_url=None,
                title=str(snippet.get("title") or ""),
                description=str(snippet.get("description") or ""),
                language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=license_enum,
                license_url="https://creativecommons.org/licenses/by/3.0/",
                author=snippet.get("channelTitle"),
                published_at=_parse_iso(snippet.get("publishedAt")),
                keywords=[str(k) for k in keywords],
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key or os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
            return []
        params_search = {
            "type": "video",
            "videoLicense": "creativeCommon",
            "part": "snippet",
            "q": " ".join(query.terms),
            "maxResults": str(min(query.max_results, 50)),
            "key": api_key,
        }
        if query.language:
            params_search["relevanceLanguage"] = query.language
        resp = self.client().get(SEARCH_URL, params=params_search)
        resp.raise_for_status()
        payload = resp.json()

        ids = []
        for item in payload.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if vid:
                ids.append(vid)
        if not ids:
            return []
        details = self.client().get(
            VIDEOS_URL,
            params={
                "id": ",".join(ids),
                "part": "contentDetails,snippet,status",
                "key": api_key,
            },
        )
        details.raise_for_status()
        detail_payload = details.json()
        return self.parse(detail_payload, query)
