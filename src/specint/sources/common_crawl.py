"""Common Crawl recipe-page adapter.

We do not pull WARCs in this module. Instead, we expose a `parse(html)`
function that extracts `schema.org/Recipe` and `schema.org/VideoObject`
JSON-LD blocks from a single HTML page. A live `search()` implementation
would feed this `parse` from a WARC iterator (out of scope for the seed
PR — the unit tests cover the HTML-parsing path against a fixture).

Page-level license detection follows three signals, in order:
  1. ``<link rel="license" href="...">`` — the HTML5 spec signal.
  2. ``<meta name="dcterms.license"|"DC.rights" content="...">`` — Dublin Core.
  3. Visible ``<a href="https://creativecommons.org/licenses/...">`` link in
     the document body (page-level copyleft/badge convention).
We ignore any CC badge that lives *inside* an embedded video player's
own block, since those describe the video provider's own site chrome,
not the page content we would legally be relying on.
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


_CC_URL_RE = re.compile(
    r"https?://(?:creativecommons\.org/(?:licenses|publicdomain)/[^\s\"'<>]+)",
    re.IGNORECASE,
)


def classify_cc_url(url: str) -> License:
    """Map a creativecommons.org URL to the License enum.

    Conservative: unknown license variants map to UNKNOWN rather than
    being promoted into a redistributable tier.
    """
    if not url:
        return License.UNKNOWN
    u = url.lower()
    if "publicdomain/zero" in u or "/cc0/" in u or u.endswith("/cc0"):
        return License.CC0
    if "publicdomain/mark" in u or "publicdomain" in u:
        return License.PUBLIC_DOMAIN
    if "by-nc" in u or "by-nd" in u:
        return License.RESTRICTED
    if "by-sa" in u:
        return License.CC_BY_SA
    if "/by/" in u or u.endswith("/by") or "licenses/by/" in u:
        return License.CC_BY
    return License.UNKNOWN


def detect_page_license(soup: BeautifulSoup) -> tuple[License, str | None]:
    """Return (License, license_url) inferred from HTML page-level signals.

    Pure function on a parsed soup. Returns (UNKNOWN, None) when no
    confident page-level signal is present.
    """
    for link in soup.find_all("link", attrs={"rel": True}):
        rels = link.get("rel") or []
        if isinstance(rels, str):
            rels = [rels]
        if "license" in [str(r).lower() for r in rels]:
            href = (link.get("href") or "").strip()
            cls = classify_cc_url(href)
            if cls is not License.UNKNOWN or href:
                return cls, (href or None)

    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").strip().lower()
        if name in {"dcterms.license", "dc.rights", "dc.license", "license"}:
            content = (meta.get("content") or "").strip()
            cls = classify_cc_url(content)
            if cls is not License.UNKNOWN or content:
                return cls, (content or None)

    body = soup.body or soup
    for a in body.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        if _CC_URL_RE.match(href):
            cls = classify_cc_url(href)
            if cls is not License.UNKNOWN:
                return cls, href

    return License.UNKNOWN, None


def parse_recipe_html(html: str, page_url: str, query: SourceQuery) -> list[VideoRecord]:
    soup = BeautifulSoup(html, "lxml")
    page_license, page_license_url = detect_page_license(soup)
    blocks: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            blocks.extend(_walk_jsonld(json.loads(tag.string or "")))
        except (json.JSONDecodeError, TypeError):
            continue

    videos = [b for b in blocks if "VideoObject" in _node_types(b)]
    recipes = [b for b in blocks if "Recipe" in _node_types(b)]
    recipe = recipes[0] if recipes else None

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
            license_url=page_license_url,
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
