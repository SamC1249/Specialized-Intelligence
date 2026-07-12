"""Common Crawl recipe-page adapter.

We do not pull WARCs in this module. Instead, we expose a `parse(html)`
function that extracts `schema.org/Recipe` and `schema.org/VideoObject`
JSON-LD blocks from a single HTML page. A live `search()` implementation
would feed this `parse` from a WARC iterator (out of scope for the seed
PR — the unit tests cover the HTML-parsing path against a fixture).

We assign `License.UNKNOWN` by default. A page-level license MUST be
proven before any record is treated as redistributable. The following
signals count as page-level license proof (in order of preference):

- `<link rel="license" href="...">`
- `<meta name="dcterms.rights" content="...">` /
  `<meta name="dc.rights" ...>`
- `<meta name="license" content="...">` (Wikibooks / OER style)
- `<meta property="og:license" content="...">`
- Any `<a>` inside the document whose `href` points at
  `creativecommons.org/{publicdomain,licenses}/{zero,by,by-sa,mark}/...`.

Each of these is compared against `_URL_LICENSE_TABLE`; only well-known
CC / PD URL prefixes upgrade a record from `UNKNOWN` to a
redistributable license. Nothing here is a heuristic on prose ("This
work is free"): we require a machine-readable license URL. The
extracted `license_url` is stamped on every record on that page.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

ISO8601_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)

# Ordered so more-specific matches win first (e.g. by-sa before by).
_URL_LICENSE_TABLE: tuple[tuple[str, License], ...] = (
    ("creativecommons.org/publicdomain/zero", License.CC0),
    ("creativecommons.org/publicdomain/mark", License.PUBLIC_DOMAIN),
    ("creativecommons.org/publicdomain", License.PUBLIC_DOMAIN),
    ("creativecommons.org/licenses/by-sa", License.CC_BY_SA),
    ("creativecommons.org/licenses/by-nc", License.RESTRICTED),
    ("creativecommons.org/licenses/by-nd", License.RESTRICTED),
    ("creativecommons.org/licenses/by/", License.CC_BY),
)


def _license_from_url(url: str) -> License:
    u = url.lower()
    for needle, lic in _URL_LICENSE_TABLE:
        if needle in u:
            return lic
    return License.UNKNOWN


def extract_page_license(soup: BeautifulSoup) -> tuple[License, str | None]:
    """Return (License, license_url) for a page, or (UNKNOWN, None).

    We only upgrade past UNKNOWN if we find a machine-readable license
    URL that matches `_URL_LICENSE_TABLE`. Free-form prose ("this work
    is CC-licensed") is intentionally ignored — we need a link a
    downstream auditor can click.
    """
    candidates: list[str] = []
    for link in soup.find_all("link", attrs={"rel": True, "href": True}):
        rel = link.get("rel")
        rels = rel if isinstance(rel, list) else [rel]
        if any(str(r).lower() == "license" for r in rels):
            candidates.append(str(link.get("href")))

    meta_names = ("dcterms.rights", "dc.rights", "license")
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or "").lower()
        prop = (meta.get("property") or "").lower()
        if name in meta_names or prop in ("og:license",):
            content = meta.get("content")
            if content:
                candidates.append(str(content))

    for a in soup.find_all("a", href=True):
        href = str(a.get("href"))
        if "creativecommons.org/" in href.lower():
            candidates.append(href)

    for c in candidates:
        lic = _license_from_url(c)
        if lic is not License.UNKNOWN:
            return lic, c
    return License.UNKNOWN, None


def parse_iso8601_duration(value: str | None) -> float | None:
    if not value or not isinstance(value, str):
        return None
    m = ISO8601_DURATION_RE.match(value.strip())
    if not m:
        return None
    parts = {k: int(v) if v else 0 for k, v in m.groupdict().items()}
    return float(
        parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
    )


def _walk_jsonld(node: Any) -> list[dict[str, Any]]:
    """Yield every dict in a (possibly nested) JSON-LD structure."""
    out: list[dict[str, Any]] = []
    if isinstance(node, list):
        for item in node:
            out.extend(_walk_jsonld(item))
    elif isinstance(node, dict):
        out.append(node)
        for v in node.values():
            out.extend(_walk_jsonld(v))
    return out


def _node_types(node: dict[str, Any]) -> set[str]:
    t = node.get("@type")
    if isinstance(t, list):
        return {str(x) for x in t}
    if isinstance(t, str):
        return {t}
    return set()


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)) and value:
        return _safe_str(value[0])
    return str(value)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_recipe_html(html: str, page_url: str, query: SourceQuery) -> list[VideoRecord]:
    soup = BeautifulSoup(html, "lxml")
    blocks: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            blocks.extend(_walk_jsonld(json.loads(tag.string or "")))
        except (json.JSONDecodeError, TypeError):
            continue

    videos = [b for b in blocks if "VideoObject" in _node_types(b)]
    recipes = [b for b in blocks if "Recipe" in _node_types(b)]
    recipe = recipes[0] if recipes else None

    page_license, page_license_url = extract_page_license(soup)

    prov = Provenance(
        extractor=__name__,
        fetched_at=utcnow(),
        query=query.serialize(),
    )

    out: list[VideoRecord] = []
    for v in videos:
        embed = _safe_str(v.get("embedUrl") or v.get("contentUrl") or page_url)
        native_id = _safe_str(v.get("@id") or v.get("identifier") or embed)
        steps: list[str] = []
        if recipe:
            instructions = recipe.get("recipeInstructions")
            if isinstance(instructions, list):
                for step in instructions:
                    if isinstance(step, dict):
                        steps.append(_safe_str(step.get("text") or step.get("name")))
                    elif isinstance(step, str):
                        steps.append(step)
            elif isinstance(instructions, str):
                steps = [s.strip() for s in instructions.split(".") if s.strip()]

        record = VideoRecord(
            id=f"common_crawl:{native_id}",
            source="common_crawl",
            source_native_id=native_id,
            url=page_url,
            media_url=None,
            title=_safe_str(v.get("name") or (recipe.get("name") if recipe else "")),
            description=_safe_str(
                v.get("description") or (recipe.get("description") if recipe else "")
            ),
            language=None,
            duration_s=parse_iso8601_duration(v.get("duration")),
            width=int(v["width"]) if isinstance(v.get("width"), (int, float)) else None,
            height=int(v["height"]) if isinstance(v.get("height"), (int, float)) else None,
            fps=None,
            license=page_license,
            license_url=page_license_url if page_license_url else None,
            author=_safe_str(
                (v.get("author") or {}).get("name")
                if isinstance(v.get("author"), dict)
                else v.get("author")
            )
            or None,
            published_at=_parse_iso(_safe_str(v.get("uploadDate")) or None),
            keywords=[
                k
                for k in (
                    recipe.get("keywords").split(",")
                    if recipe and isinstance(recipe.get("keywords"), str)
                    else []
                )
                if k.strip()
            ],
            recipe_steps=[s for s in steps if s],
            provenance=prov,
        )
        out.append(record)
    return out


class CommonCrawlRecipeSource(BaseSource):
    slug = "common_crawl"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        html = raw.get("html")
        url = raw.get("url")
        if not isinstance(html, str) or not isinstance(url, str):
            return []
        return parse_recipe_html(html, url, query)

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        # Live WARC iteration is out of scope for the seed PR.
        return []
