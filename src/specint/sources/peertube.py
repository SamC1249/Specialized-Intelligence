"""PeerTube adapter.

PeerTube is a federated video host. Each instance exposes
`/api/v1/search/videos` with a `licenceOneOf` filter. We default to a
small allowlist of large instances and only keep records whose declared
licence is CC-BY / CC-BY-SA / CC0 / Public Domain.

PeerTube licence IDs (per upstream docs):
  1 = Attribution (CC-BY)
  2 = Attribution - Share Alike (CC-BY-SA)
  3 = Attribution - No Derivatives  (we exclude — not redistributable)
  4 = Attribution - Non Commercial (we exclude)
  5 = Attribution - Non Commercial - Share Alike (we exclude)
  6 = Attribution - Non Commercial - No Derivatives (we exclude)
  7 = Public Domain Dedication (CC0)
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from specint.records import License, Provenance, SourceQuery, VideoRecord, utcnow
from specint.sources.base import BaseSource

DEFAULT_INSTANCES: tuple[str, ...] = (
    "https://framatube.org",
    "https://video.blender.org",
    "https://tilvids.com",
)
ALLOWED_LICENCE_IDS = {1, 2, 7}


def _peertube_license(licence_id: int | None) -> License:
    if licence_id == 1:
        return License.CC_BY
    if licence_id == 2:
        return License.CC_BY_SA
    if licence_id == 7:
        return License.CC0
    return License.UNKNOWN


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class PeerTubeSource(BaseSource):
    slug = "peertube"

    def __init__(self, instances: tuple[str, ...] = DEFAULT_INSTANCES, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.instances = instances

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        if not isinstance(raw, dict):
            return []
        data = raw.get("data") or []
        instance = raw.get("__instance__", "")
        prov = Provenance(
            extractor=__name__,
            fetched_at=utcnow(),
            query=query.serialize(),
        )
        out: list[VideoRecord] = []
        for v in data:
            licence = (v.get("licence") or {}).get("id")
            if licence not in ALLOWED_LICENCE_IDS:
                continue
            uuid = v.get("uuid") or v.get("shortUUID") or v.get("id")
            if not uuid:
                continue
            host = v.get("account", {}).get("host") or instance.replace("https://", "")
            url = f"https://{host}/videos/watch/{uuid}"
            license_enum = _peertube_license(licence)
            files = v.get("files") or []
            media_url = files[0].get("fileUrl") if files else None
            language = (v.get("language") or {}).get("id")

            record = VideoRecord(
                id=f"peertube:{host}:{uuid}",
                source="peertube",
                source_native_id=str(uuid),
                url=url,
                media_url=media_url if license_enum.is_redistributable else None,
                title=str(v.get("name") or ""),
                description=str(v.get("description") or ""),
                language=language,
                duration_s=float(v["duration"]) if v.get("duration") is not None else None,
                width=None,
                height=int(v["resolution"]["id"])
                if isinstance(v.get("resolution"), dict) and v["resolution"].get("id")
                else None,
                fps=None,
                license=license_enum,
                license_url=None,
                author=(v.get("account") or {}).get("displayName"),
                published_at=_parse_iso(v.get("publishedAt")),
                keywords=list(v.get("tags") or []),
                recipe_steps=[],
                provenance=prov,
            )
            out.append(record)
        return out

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        all_records: list[VideoRecord] = []
        for instance in self.instances:
            params = {
                "search": " ".join(query.terms),
                "count": str(min(query.max_results, 25)),
                "licenceOneOf[]": [str(i) for i in sorted(ALLOWED_LICENCE_IDS)],
            }
            try:
                resp = self.client().get(f"{instance}/api/v1/search/videos", params=params)
                resp.raise_for_status()
                payload = resp.json()
                payload["__instance__"] = instance
            except Exception:
                continue
            all_records.extend(self.parse(payload, query))
        return all_records
