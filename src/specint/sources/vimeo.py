"""Vimeo CC adapter.

Vimeo exposes a public API with a Creative-Commons filter:

    GET https://api.vimeo.com/videos?query=...&filter=CC&sort=relevant

The response's per-video `license` field is one of:
    by, by-sa, by-nc, by-nc-sa, by-nd, by-nc-nd, cc0

We only treat `by`, `by-sa`, `cc0` as redistributable. Everything else
is dropped. The `filter=CC` server-side filter is only a *hint* — the
per-item field is authoritative. We re-check both and refuse to emit a
`media_url` for anything that fails.

Live `search()` requires the environment variable `VIMEO_API_TOKEN`;
unit tests exercise `parse()` with a checked-in fixture modelled on the
documented response shape:

    https://developer.vimeo.com/api/reference/response/video

Multilingual search terms are a TODO — today we pass through whatever
`query.terms` is given, which keeps the adapter language-neutral at
the cost of yield on non-English cooking vocabulary. The adversarial
plan for the day explicitly flags this.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_URL = "https://api.vimeo.com/videos"

# Per Vimeo's API reference. `by-nc*` and `-nd` variants are intentionally
# excluded: they are not redistribution-safe under our hard constraints.
_LICENSE_MAP: dict[str, License] = {
    "cc0": License.CC0,
    "by": License.CC_BY,
    "by-sa": License.CC_BY_SA,
}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _vimeo_native_id(uri: str | None, link: str | None) -> str | None:
    """Vimeo video IDs appear in `uri` as `/videos/<id>` or at the tail of `link`."""
    if uri and "/videos/" in uri:
        return uri.rsplit("/", 1)[-1] or None
    if link:
        tail = link.rstrip("/").rsplit("/", 1)[-1]
        if tail.isdigit():
            return tail
    return None


def _pick_file(files: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Prefer the highest-resolution progressive MP4 file."""
    if not files:
        return None
    progressive = [f for f in files if (f.get("quality") or "").lower() != "hls"]
    pool = progressive or files
    return max(pool, key=lambda f: int(f.get("height") or 0), default=None)


class VimeoCCSource(BaseSource):
    slug = "vimeo"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        data = raw.get("data") or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for v in data:
            raw_license = (v.get("license") or "").strip().lower()
            license_enum = _LICENSE_MAP.get(raw_license, License.UNKNOWN)
            if license_enum is License.UNKNOWN:
                continue

            native = _vimeo_native_id(v.get("uri"), v.get("link"))
            if not native:
                continue
            page_url = v.get("link") or f"https://vimeo.com/{native}"
            file_info = _pick_file(v.get("files"))
            media_url = file_info.get("link") if file_info else None

            user = v.get("user") or {}
            tags = v.get("tags") or []
            keywords = [str(t.get("name")) for t in tags if isinstance(t, dict) and t.get("name")]

            record = VideoRecord(
                id=f"vimeo:{native}",
                source="vimeo",
                source_native_id=native,
                url=page_url,
                media_url=media_url if license_enum.is_redistributable else None,
                title=str(v.get("name") or ""),
                description=str(v.get("description") or ""),
                language=v.get("language") if isinstance(v.get("language"), str) else None,
                duration_s=float(v["duration"]) if v.get("duration") is not None else None,
                width=int(v["width"]) if isinstance(v.get("width"), int) else None,
                height=int(v["height"]) if isinstance(v.get("height"), int) else None,
                fps=None,
                license=license_enum,
                license_url=f"https://creativecommons.org/licenses/{raw_license}/4.0/"
                if raw_license not in {"cc0"}
                else "https://creativecommons.org/publicdomain/zero/1.0/",
                author=str(user.get("name")) if user.get("name") else None,
                published_at=_parse_iso(v.get("release_time") or v.get("created_time")),
                keywords=keywords,
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        token = os.environ.get("VIMEO_API_TOKEN")
        if not token:
            # We refuse to run without a token. Static analysis of the adapter
            # remains possible via `parse()` + fixtures.
            return []
        params: dict[str, Any] = {
            "query": " ".join(query.terms),
            "filter": "CC",
            "sort": "relevant",
            "direction": "desc",
            "per_page": str(min(query.max_results, 50)),
            "page": "1",
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = self.client().get(API_URL, params=params, headers=headers)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
