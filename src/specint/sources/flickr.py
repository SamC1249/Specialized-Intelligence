"""Flickr CC-licensed video adapter.

Flickr hosts short videos (Flickr limits to a few minutes) alongside
photos. The `flickr.photos.search` API accepts a `license` filter whose
numeric codes correspond to specific Creative Commons licences, plus a
`media=videos` filter to restrict to video. We only treat the codes
corresponding to **redistribution-permissive** Creative Commons tiers
as license-clean.

Flickr licence codes (per `flickr.photos.licenses.getInfo`):

    0  All Rights Reserved        (reject)
    1  CC BY-NC-SA                 (reject — NC)
    2  CC BY-NC                    (reject — NC)
    3  CC BY-NC-ND                 (reject — NC + ND)
    4  CC BY                       (CC_BY)
    5  CC BY-SA                    (CC_BY_SA)
    6  CC BY-ND                    (reject — ND)
    7  No known copyright restr.   (PUBLIC_DOMAIN)
    8  US-Government Work          (PUBLIC_DOMAIN)
    9  CC0                         (CC0)
    10 Public Domain Mark          (PUBLIC_DOMAIN)

Flickr's API ToS permits automated use with an API key and attribution
to the photographer. We never store the media bytes; we store the
canonical Flickr landing-page URL and, for license-clean records, the
`media_url` pointer. Live `search()` requires `FLICKR_API_KEY`.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

API_URL = "https://api.flickr.com/services/rest/"

_LICENSE_BY_CODE: dict[int, License] = {
    0: License.RESTRICTED,
    1: License.RESTRICTED,
    2: License.RESTRICTED,
    3: License.RESTRICTED,
    4: License.CC_BY,
    5: License.CC_BY_SA,
    6: License.RESTRICTED,
    7: License.PUBLIC_DOMAIN,
    8: License.PUBLIC_DOMAIN,
    9: License.CC0,
    10: License.PUBLIC_DOMAIN,
}
ALLOWED_LICENSE_CODES = tuple(
    sorted(code for code, lic in _LICENSE_BY_CODE.items() if lic.is_redistributable)
)

_LICENSE_URL: dict[License, str] = {
    License.CC_BY: "https://creativecommons.org/licenses/by/2.0/",
    License.CC_BY_SA: "https://creativecommons.org/licenses/by-sa/2.0/",
    License.CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
    License.PUBLIC_DOMAIN: "https://creativecommons.org/publicdomain/mark/1.0/",
}


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_unix(value: Any) -> datetime | None:
    v = _coerce_int(value)
    if v is None or v <= 0:
        return None
    return datetime.fromtimestamp(v, tz=UTC)


def _page_url(photo: dict[str, Any]) -> str:
    owner = photo.get("owner") or ""
    pid = photo.get("id") or ""
    path_alias = photo.get("pathalias") or owner
    return f"https://www.flickr.com/photos/{path_alias}/{pid}/"


def _media_url(photo: dict[str, Any]) -> str | None:
    """Prefer the largest known-direct video URL. Fallbacks are deliberate."""
    for key in ("url_o", "url_l", "url_c", "url_z", "url_m"):
        value = photo.get(key)
        if isinstance(value, str) and value:
            return value
    secret = photo.get("secret")
    server = photo.get("server")
    pid = photo.get("id")
    if secret and server and pid:
        return f"https://live.staticflickr.com/{server}/{pid}_{secret}_b.jpg"
    return None


class FlickrCCSource(BaseSource):
    slug = "flickr"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        photos = (raw.get("photos") or {}).get("photo") or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for p in photos:
            if (p.get("media") or "").lower() != "video":
                continue
            license_code = _coerce_int(p.get("license"))
            license_enum = _LICENSE_BY_CODE.get(license_code or -1, License.UNKNOWN)
            if not license_enum.is_redistributable:
                continue
            pid = p.get("id")
            if not pid:
                continue
            page_url = _page_url(p)
            media_url = _media_url(p) if license_enum.is_redistributable else None

            width = _coerce_int(p.get("width_o") or p.get("o_width") or p.get("width_l"))
            height = _coerce_int(p.get("height_o") or p.get("o_height") or p.get("height_l"))
            duration = p.get("duration")
            duration_s: float | None
            try:
                duration_s = float(duration) if duration is not None else None
            except (TypeError, ValueError):
                duration_s = None

            tags_field = p.get("tags") or ""
            keywords = [t for t in tags_field.split() if t]

            record = VideoRecord(
                id=f"flickr:{pid}",
                source="flickr",
                source_native_id=str(pid),
                url=page_url,
                media_url=media_url,
                title=str(p.get("title") or ""),
                description=str((p.get("description") or {}).get("_content") or ""),
                language=None,
                duration_s=duration_s,
                width=width,
                height=height,
                fps=None,
                license=license_enum,
                license_url=_LICENSE_URL.get(license_enum),
                author=str(p.get("ownername")) if p.get("ownername") else None,
                published_at=_parse_unix(p.get("dateupload")),
                keywords=keywords,
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        api_key = os.environ.get("FLICKR_API_KEY")
        if not api_key:
            return []
        params = {
            "method": "flickr.photos.search",
            "api_key": api_key,
            "text": " ".join(query.terms),
            "license": ",".join(str(code) for code in ALLOWED_LICENSE_CODES),
            "media": "videos",
            "sort": "relevance",
            "per_page": str(min(query.max_results, 100)),
            "page": "1",
            "safe_search": "1",
            "extras": "license,description,date_upload,owner_name,tags,media,url_o,url_l,url_c,path_alias,o_dims",
            "format": "json",
            "nojsoncallback": "1",
        }
        resp = self.client().get(API_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
