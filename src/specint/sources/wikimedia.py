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


def _coerce_license(short_name: str | None) -> tuple[License, float]:
    """Return (license, confidence) for a Wikimedia ``LicenseShortName`` string.

    High-confidence (≥0.9) only when the upstream string is unambiguous (the
    full canonical token, e.g. ``CC0``, ``CC-BY-SA-4.0``). Fallback substring
    matches drop to 0.6 so downstream consumers can choose to exclude them.
    """
    if not short_name:
        return License.UNKNOWN, 0.0
    raw = short_name.strip()
    s = raw.upper().replace(" ", "")
    if s.startswith("CC0") or s == "PUBLICDOMAIN":
        return License.CC0 if s.startswith("CC0") else License.PUBLIC_DOMAIN, 1.0
    if s in {"CC-BY-SA-4.0", "CC-BY-SA-3.0", "CC-BY-SA-2.5", "CC-BY-SA-2.0"}:
        return License.CC_BY_SA, 0.95
    if s in {"CC-BY-4.0", "CC-BY-3.0", "CC-BY-2.5", "CC-BY-2.0"}:
        return License.CC_BY, 0.95
    if "BY-NC" in s or "BYNC" in s or "BY-ND" in s or "BYND" in s:
        return License.RESTRICTED, 0.9
    if "BY-SA" in s or "BYSA" in s:
        return License.CC_BY_SA, 0.6
    if "CC-BY" in s or "CCBY" in s:
        return License.CC_BY, 0.6
    if "PUBLICDOMAIN" in s or s == "PD":
        return License.PUBLIC_DOMAIN, 0.6
    return License.UNKNOWN, 0.0


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
            license_enum, license_conf = _coerce_license(license_value)

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
                license_confidence=license_conf,
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
