"""Openverse adapter.

Openverse (openverse.org / WordPress Foundation) aggregates
permissively-licensed media across many upstream sources — Wikimedia,
Flickr's CC pool, Europeana, Museums Victoria, and others. It's a
first-party aggregator whose entire scope is legal, redistributable
content, which is exactly our allowlist criterion.

We use the public JSON API at:
  https://api.openverse.org/v1/audio/  (audio + video — video support
  is an emerging endpoint at the time of writing; we accept either
  content type but only emit records that look like video via
  `filetype` / mime).

Key adapter rules:
  - We store the upstream provider (`foreign_landing_url`,
    `provider`) so provenance is preserved.
  - License classification is delegated to `specint.licenses` so we
    don't drift from the other adapters.
  - Non-redistributable (BY-NC / BY-ND / etc.) records are dropped
    hard — Openverse should never return them, but we defend anyway.

`search()` is a network call and is not exercised by unit tests;
`parse()` is pure and is covered by a fixture-driven test.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.licenses import classify
from specint.records import Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://api.openverse.org/v1/video/"


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _cc_url_from_short(name: str | None) -> str | None:
    if not name:
        return None
    s = name.strip().lower()
    mapping = {
        "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
        "pdm": "https://creativecommons.org/publicdomain/mark/1.0/",
        "by": "https://creativecommons.org/licenses/by/4.0/",
        "by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
    }
    return mapping.get(s)


class OpenverseSource(BaseSource):
    slug = "openverse"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        results = raw.get("results") or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for item in results:
            identifier = item.get("id") or item.get("identifier")
            if not identifier:
                continue

            license_url = item.get("license_url") or _cc_url_from_short(item.get("license"))
            verdict = classify(url=license_url, short_name=item.get("license"))
            if not verdict.is_redistributable:
                continue

            url = item.get("foreign_landing_url") or item.get("url") or license_url
            if not url:
                continue
            media_url = item.get("url") if verdict.is_redistributable else None

            filetype = (item.get("filetype") or "").lower()
            mime = (item.get("mime_type") or "").lower()
            if (
                filetype
                and filetype not in {"mp4", "webm", "ogv", "mov"}
                and not mime.startswith("video/")
            ):
                continue

            width = item.get("width") if isinstance(item.get("width"), int) else None
            height = item.get("height") if isinstance(item.get("height"), int) else None
            duration = item.get("duration")
            duration_s: float | None = None
            if isinstance(duration, (int, float)):
                duration_s = float(duration) / (1000.0 if duration > 3600 else 1.0)

            tags_raw = item.get("tags") or []
            keywords: list[str] = []
            if isinstance(tags_raw, list):
                for t in tags_raw:
                    if isinstance(t, dict) and isinstance(t.get("name"), str):
                        keywords.append(t["name"])
                    elif isinstance(t, str):
                        keywords.append(t)

            record = VideoRecord(
                id=f"openverse:{identifier}",
                source="openverse",
                source_native_id=str(identifier),
                url=url,
                media_url=media_url,
                title=str(item.get("title") or ""),
                description=str(item.get("description") or ""),
                language=item.get("language") if isinstance(item.get("language"), str) else None,
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=verdict.license,
                license_url=license_url or None,
                author=item.get("creator") if isinstance(item.get("creator"), str) else None,
                published_at=_parse_iso(item.get("indexed_on") or item.get("created_on")),
                keywords=keywords,
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        params = {
            "q": " ".join(query.terms),
            "page_size": str(min(query.max_results, 20)),
            "license_type": "commercial,modification",
        }
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
