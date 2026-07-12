"""Wikimedia Commons adapter.

Uses the MediaWiki action API:
  https://commons.wikimedia.org/w/api.php
with `action=query&generator=search&gsrnamespace=6&prop=imageinfo&iiprop=url|size|mime|extmetadata`.

Commons hosts CC0 / CC-BY / CC-BY-SA / public-domain media. License is
extracted from `extmetadata.LicenseShortName`.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.quality.license_utils import classify
from specint.records import Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_URL = "https://commons.wikimedia.org/w/api.php"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class WikimediaCommonsSource(BaseSource):
    slug = "wikimedia"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        pages = (raw.get("query") or {}).get("pages") or {}
        out: list[VideoRecord] = []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        for page_id, page in pages.items():
            title = page.get("title") or ""
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            mime = (info.get("mime") or "").lower()
            if not mime.startswith("video/") and not title.lower().endswith(
                (".webm", ".ogv", ".mp4")
            ):
                continue

            ext = info.get("extmetadata") or {}
            license_value = (ext.get("LicenseShortName") or {}).get("value")
            artist = (ext.get("Artist") or {}).get("value")
            published = _parse_iso((ext.get("DateTimeOriginal") or {}).get("value"))
            license_url = (ext.get("LicenseUrl") or {}).get("value") or None

            url = info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{title}"
            media_url = info.get("url")
            license_enum = classify(license_value, license_url)

            record = VideoRecord(
                id=f"wikimedia:{page_id}",
                source="wikimedia",
                source_native_id=str(page_id),
                url=url,
                media_url=media_url if license_enum.is_redistributable else None,
                title=title,
                description="",
                language=None,
                duration_s=info.get("duration"),
                width=info.get("width"),
                height=info.get("height"),
                fps=None,
                license=license_enum,
                license_url=license_url if license_url else None,
                author=artist,
                published_at=published,
                keywords=[],
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": " ".join(query.terms) + " filetype:video",
            "gsrnamespace": "6",
            "gsrlimit": str(min(query.max_results, 50)),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
        }
        resp = self.client().get(API_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
