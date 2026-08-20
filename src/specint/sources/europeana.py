"""Europeana Search API adapter.

Europeana aggregates ~60M cultural-heritage records from thousands of
European institutions. Video items are filtered with
`qf=TYPE:VIDEO` and license-clean records are those whose `rights`
value points at a Creative Commons or Public Domain declaration.

Endpoint (v2, JSON):
  https://api.europeana.eu/record/v2/search.json
    ?query=<terms>
    &qf=TYPE:VIDEO
    &qf=RIGHTS:*creative*
    &qf=RIGHTS:*publicdomain*
    &rows=<n>
    &wskey=<key>

The API key is free but required for live calls. We keep the adapter
offline-testable by making `parse(raw)` a pure function over the
documented JSON response shape; `search()` will refuse to run without
`SPECINT_EUROPEANA_KEY` and `SPECINT_RUN_INTEGRATION=1`.

Rights heterogeneity notes:
  Europeana surfaces at least three families of rights URLs:
    * creativecommons.org/licenses/…  (CC-BY, CC-BY-SA, CC-BY-NC …)
    * creativecommons.org/publicdomain/…  (CC0, PDM)
    * rightsstatements.org/…            (RS-*; NOT redistributable)
  We default RS-* and any unknown rights value to License.UNKNOWN.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SEARCH_URL = "https://api.europeana.eu/record/v2/search.json"


def _license_from_rights(rights: Any) -> License:
    """Map a Europeana `rights` field (str | list[str] | None) to a License.

    We look at *all* URLs when a list is provided and pick the most
    restrictive interpretation that is still redistributable. If any
    single URL is a Rights-Statement (rightsstatements.org/*) we fall
    back to UNKNOWN rather than trying to be clever.
    """
    if rights is None:
        return License.UNKNOWN
    urls: list[str] = []
    if isinstance(rights, list):
        urls = [str(x) for x in rights if isinstance(x, str)]
    elif isinstance(rights, str):
        urls = [rights]
    if not urls:
        return License.UNKNOWN

    normalized = [u.lower() for u in urls]
    if any("rightsstatements.org" in u for u in normalized):
        return License.UNKNOWN
    if any(("by-nc" in u) or ("by-nd" in u) for u in normalized):
        return License.RESTRICTED
    if any(("publicdomain/zero" in u) or ("/cc0" in u) for u in normalized):
        return License.CC0
    if any("publicdomain/mark" in u for u in normalized):
        return License.PUBLIC_DOMAIN
    if any("by-sa" in u for u in normalized):
        return License.CC_BY_SA
    if any(("creativecommons.org/licenses/by/" in u) or ("/licenses/by/" in u) for u in normalized):
        return License.CC_BY
    if any("publicdomain" in u for u in normalized):
        return License.PUBLIC_DOMAIN
    return License.UNKNOWN


def _pick_lang_aware(field: Any, prefer: str | None = None) -> str:
    """Europeana returns many text fields as {lang: [values]} maps.

    Return a single string, preferring `prefer` (e.g. "en") if present.
    """
    if field is None:
        return ""
    if isinstance(field, str):
        return field
    if isinstance(field, list) and field:
        first = field[0]
        return str(first) if not isinstance(first, dict) else _pick_lang_aware(first, prefer)
    if isinstance(field, dict):
        if prefer and prefer in field:
            v = field[prefer]
            if isinstance(v, list) and v:
                return str(v[0])
            if isinstance(v, str):
                return v
        for _, v in field.items():
            if isinstance(v, list) and v:
                return str(v[0])
            if isinstance(v, str):
                return v
    return ""


def _first_str(field: Any) -> str | None:
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, list) and field:
        item = field[0]
        return str(item) if isinstance(item, (str, int, float)) else None
    return None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class EuropeanaSource(BaseSource):
    slug = "europeana"

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
            item_type = item.get("type")
            if item_type and item_type not in {"VIDEO", "MOVING_IMAGE"}:
                continue

            rights = item.get("rights")
            license_enum = _license_from_rights(rights)

            europeana_id = _first_str(item.get("id")) or _first_str(item.get("guid"))
            if not europeana_id:
                continue

            landing = (
                _first_str(item.get("guid")) or f"https://www.europeana.eu/en/item{europeana_id}"
            )
            media_url = _first_str(item.get("edmIsShownBy"))
            title = _pick_lang_aware(item.get("dcTitleLangAware") or item.get("title"), "en")
            description = _pick_lang_aware(
                item.get("dcDescriptionLangAware") or item.get("dcDescription"), "en"
            )
            language = _first_str(item.get("language"))
            author = _first_str(item.get("dcCreator")) or _first_str(item.get("edmDataProvider"))
            license_url = _first_str(rights)
            published_at = _parse_iso(_first_str(item.get("timestamp_created")))
            keywords: list[str] = []
            subjects = item.get("dcSubject")
            if isinstance(subjects, list):
                keywords = [str(s) for s in subjects if isinstance(s, (str, int, float))]

            record = VideoRecord(
                id=f"europeana:{europeana_id}",
                source="europeana",
                source_native_id=europeana_id,
                url=landing,
                media_url=media_url if (media_url and license_enum.is_redistributable) else None,
                title=title,
                description=description,
                language=language,
                duration_s=None,
                width=None,
                height=None,
                fps=None,
                license=license_enum,
                license_url=license_url,
                author=author,
                published_at=published_at,
                keywords=keywords,
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        key = os.environ.get("SPECINT_EUROPEANA_KEY")
        if not key:
            raise RuntimeError("Europeana search requires SPECINT_EUROPEANA_KEY (free API key).")
        params = {
            "query": " ".join(query.terms),
            "qf": ["TYPE:VIDEO", "RIGHTS:*creative*"],
            "rows": str(min(query.max_results, 50)),
            "wskey": key,
            "media": "true",
        }
        resp = self.client().get(SEARCH_URL, params=params)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
