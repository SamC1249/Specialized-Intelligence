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

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_URL = "https://commons.wikimedia.org/w/api.php"


_WS_RE = None  # populated below


def _normalise_license_string(short_name: str) -> str:
    # Strip every unicode whitespace (incl. NBSP U+00A0, thin spaces),
    # uppercase, and drop hyphens so "BY-NC" and "BYNC" collide.
    cleaned = []
    for ch in short_name:
        if ch.isspace() or ord(ch) == 0x00A0:
            continue
        cleaned.append(ch)
    return "".join(cleaned).upper().replace("-", "")


def _coerce_license(short_name: str | None) -> License:
    if not short_name:
        return License.UNKNOWN
    s = _normalise_license_string(short_name)
    # NC / ND variants are always RESTRICTED regardless of what else is present.
    if "NONCOMMERCIAL" in s or "BYNC" in s or "NCSA" in s or "NCND" in s or "BYNCND" in s:
        return License.RESTRICTED
    if "NODERIVATIVES" in s or "NODERIV" in s or "BYND" in s:
        return License.RESTRICTED
    if s.startswith("CC0") or "CREATIVECOMMONSZERO" in s:
        return License.CC0
    if "BYSA" in s or "SHAREALIKE" in s or "ATTRIBUTIONSHAREALIKE" in s:
        return License.CC_BY_SA
    if "CCBY" in s or s.startswith("BY") or "ATTRIBUTION" in s:
        return License.CC_BY
    if "PUBLICDOMAIN" in s or s == "PD":
        return License.PUBLIC_DOMAIN
    return License.UNKNOWN


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
            license_enum = _coerce_license(license_value)

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
