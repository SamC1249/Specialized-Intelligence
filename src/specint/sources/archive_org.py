"""Internet Archive adapter.

Uses the public advancedsearch.php JSON endpoint:
  https://archive.org/advancedsearch.php?q=<...>&fl[]=...&output=json

Only items with a CC / public-domain `licenseurl` are kept license-clean.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://archive.org/advancedsearch.php"


def _license_from_url(url: str | None) -> License:
    if not url:
        return License.UNKNOWN
    u = url.lower()
    if "publicdomain/zero" in u or "cc0" in u:
        return License.CC0
    if "by-sa" in u:
        return License.CC_BY_SA
    if "by-nc" in u or "by-nd" in u:
        return License.RESTRICTED
    if "/by/" in u or u.endswith("/by") or "creativecommons.org/licenses/by/" in u:
        return License.CC_BY
    if "publicdomain" in u:
        return License.PUBLIC_DOMAIN
    return License.UNKNOWN


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class ArchiveOrgSource(BaseSource):
    slug = "archive_org"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        docs = ((raw.get("response") or {}).get("docs")) or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for d in docs:
            identifier = d.get("identifier")
            if not identifier:
                continue
            license_url = d.get("licenseurl")
            license_enum = _license_from_url(license_url)
            url = f"https://archive.org/details/{identifier}"
            media_url = (
                f"https://archive.org/download/{identifier}/{identifier}.mp4"
                if license_enum.is_redistributable
                else None
            )
            duration = d.get("runtime")
            duration_s: float | None = None
            if isinstance(duration, str) and ":" in duration:
                parts = [int(p) for p in duration.split(":") if p.isdigit()]
                if len(parts) == 3:
                    duration_s = parts[0] * 3600 + parts[1] * 60 + parts[2]
                elif len(parts) == 2:
                    duration_s = parts[0] * 60 + parts[1]
            elif isinstance(duration, (int, float)):
                duration_s = float(duration)

            keywords: list[str] = []
            kw = d.get("subject")
            if isinstance(kw, list):
                keywords = [str(k) for k in kw]
            elif isinstance(kw, str):
                keywords = [kw]

            record = VideoRecord(
                id=f"archive_org:{identifier}",
                source="archive_org",
                source_native_id=str(identifier),
                url=url,
                media_url=media_url,
                title=str(d.get("title") or identifier),
                description=str(d.get("description") or ""),
                language=d.get("language") if isinstance(d.get("language"), str) else None,
                duration_s=duration_s,
                width=None,
                height=None,
                fps=None,
                license=license_enum,
                license_url=license_url if license_url else None,
                author=d.get("creator") if isinstance(d.get("creator"), str) else None,
                published_at=_parse_iso(d.get("publicdate") or d.get("date")),
                keywords=keywords,
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        q = " AND ".join(f'"{t}"' for t in query.terms) + " AND mediatype:movies"
        params: list[tuple[str, str]] = [
            ("q", q),
            ("fl[]", "identifier"),
            ("fl[]", "title"),
            ("fl[]", "description"),
            ("fl[]", "creator"),
            ("fl[]", "subject"),
            ("fl[]", "language"),
            ("fl[]", "licenseurl"),
            ("fl[]", "runtime"),
            ("fl[]", "publicdate"),
            ("fl[]", "date"),
            ("rows", str(min(query.max_results, 50))),
            ("output", "json"),
        ]
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
