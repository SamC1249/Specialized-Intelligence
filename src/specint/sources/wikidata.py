"""Wikidata SPARQL source adapter.

Wikidata (Q-entities) has structured metadata about many CC-licensed
cooking videos: `wdt:P18` (image) and `wdt:P10` (video) with
`wdt:P275` (copyright license, itself a Q-entity). We hit the public
SPARQL endpoint at:

    https://query.wikidata.org/sparql

with `Accept: application/sparql-results+json`. This is explicitly
authorised (see `robots.txt` and the Wikidata Query Service ToS) so
long as we respect the User-Agent policy and don't batch DDOS.

We do **not** download media here. Only URL + metadata. Media URLs
returned by the SPARQL result live on `commons.wikimedia.org` — those
follow Commons licensing already covered by `wikimedia.py`. This
adapter exists to broaden yield: SPARQL returns items that the Commons
search API misses because they lack the exact keyword in the file page.

Fixture-driven test contract: `parse(raw, query)` takes the SPARQL JSON
payload with `head.vars` and `results.bindings`, one binding per row.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

SPARQL_URL = "https://query.wikidata.org/sparql"

_LICENSE_QIDS: dict[str, License] = {
    "Q6938433": License.CC0,
    "Q19125117": License.CC0,
    "Q6905323": License.CC_BY,
    "Q18199165": License.CC_BY,
    "Q19068220": License.CC_BY_SA,
    "Q18199175": License.CC_BY_SA,
    "Q19652": License.PUBLIC_DOMAIN,
    "Q71257079": License.PUBLIC_DOMAIN,
}


def _extract_qid(uri: str | None) -> str | None:
    if not uri:
        return None
    if "/" not in uri:
        return uri if uri.startswith("Q") else None
    tail = uri.rstrip("/").split("/")[-1]
    return tail if tail.startswith("Q") else None


def _license_from_qid(qid: str | None) -> License:
    if not qid:
        return License.UNKNOWN
    return _LICENSE_QIDS.get(qid, License.UNKNOWN)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _val(binding: dict[str, Any], key: str) -> str | None:
    node = binding.get(key)
    if not isinstance(node, dict):
        return None
    v = node.get("value")
    return str(v) if v is not None else None


class WikidataSource(BaseSource):
    slug = "wikidata"

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        bindings = ((raw.get("results") or {}).get("bindings")) or []
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for b in bindings:
            item_uri = _val(b, "item")
            qid = _extract_qid(item_uri)
            if not qid:
                continue
            media = _val(b, "video") or _val(b, "media")
            if not media:
                continue
            license_qid = _extract_qid(_val(b, "license"))
            license_enum = _license_from_qid(license_qid)
            title = _val(b, "itemLabel") or qid
            description = _val(b, "description") or ""
            duration_raw = _val(b, "duration")
            duration_s: float | None = None
            if duration_raw:
                try:
                    duration_s = float(duration_raw)
                except ValueError:
                    duration_s = None
            author = _val(b, "creatorLabel")
            language = _val(b, "language")
            published = _parse_iso(_val(b, "published"))
            license_url = _val(b, "licenseUrl")
            item_landing = item_uri or f"https://www.wikidata.org/wiki/{qid}"

            record = VideoRecord(
                id=f"wikidata:{qid}",
                source="wikidata",
                source_native_id=qid,
                url=item_landing,
                media_url=media if license_enum.is_redistributable else None,
                title=title,
                description=description,
                language=language,
                duration_s=duration_s,
                width=None,
                height=None,
                fps=None,
                license=license_enum,
                license_url=license_url,
                author=author,
                published_at=published,
                keywords=[],
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def build_sparql(self, query: SourceQuery) -> str:
        term = query.terms[0] if query.terms else "cooking"
        term_escaped = term.replace('"', '\\"')
        return f"""
        SELECT ?item ?itemLabel ?video ?license ?duration ?creatorLabel ?published WHERE {{
          ?item wdt:P10 ?video .
          ?item wdt:P275 ?license .
          OPTIONAL {{ ?item wdt:P2047 ?duration }}
          OPTIONAL {{ ?item wdt:P170 ?creator . }}
          OPTIONAL {{ ?item wdt:P577 ?published }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
          FILTER(CONTAINS(LCASE(?itemLabel), "{term_escaped.lower()}"))
        }} LIMIT {min(query.max_results, 50)}
        """

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        sparql = self.build_sparql(query)
        headers = {"Accept": "application/sparql-results+json"}
        resp = self.client().get(f"{SPARQL_URL}?query={quote_plus(sparql)}", headers=headers)
        resp.raise_for_status()
        return self.parse(resp.json(), query)
