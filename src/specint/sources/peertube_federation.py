"""Federated PeerTube walk.

Where `peertube.py` hits a single instance, this adapter:

1. Loads a seed instance list from `data/peertube_instances.txt` (or a
   caller-supplied iterable).
2. Fans out `search/videos` across all instances, then dedupes results
   by ActivityPub actor id (`{host}/accounts/{name}`) so cross-mirrored
   videos are counted once.
3. Still enforces the per-video licence allowlist (CC-BY / CC-BY-SA /
   CC0 / Public Domain) — same rules as the single-instance adapter,
   applied instance-by-instance so a mis-declaring instance can't leak
   restricted media into the corpus.

Live network fan-out only happens in `search()` and only when
`SPECINT_RUN_INTEGRATION=1` (kept offline by default). `parse()` is a
pure function of the merged JSON payload.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

from specint.records import SourceQuery, VideoRecord
from specint.sources.base import BaseSource
from specint.sources.peertube import ALLOWED_LICENCE_IDS, PeerTubeSource

DEFAULT_INSTANCE_FILE = Path(__file__).resolve().parents[3] / "data" / "peertube_instances.txt"


def load_instance_list(path: Path | None = None) -> list[str]:
    file = path or DEFAULT_INSTANCE_FILE
    if not file.exists():
        return []
    out: list[str] = []
    for raw_line in file.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            out.append(line.rstrip("/"))
    return out


def _actor_content_key(record: VideoRecord) -> str:
    """PeerTube's `record.id` embeds `origin_host:uuid`, so two mirrors
    of the same video collapse naturally on `.id` alone.
    """
    return record.id


class PeerTubeFederationSource(BaseSource):
    """Fans a query out over a seed list of PeerTube instances."""

    slug = "peertube_federation"

    def __init__(
        self,
        instances: Iterable[str] | None = None,
        max_concurrent: int = 4,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.instances = list(instances) if instances is not None else load_instance_list()
        self.max_concurrent = max_concurrent
        self._per_instance = PeerTubeSource(client=self._client)

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        """`raw` is either the raw instance payload (with `__instance__`)
        or a dict of `{instance_url: payload}`.
        """
        if isinstance(raw, dict) and "data" in raw:
            return self._per_instance.parse(raw, query)
        merged: list[VideoRecord] = []
        if isinstance(raw, dict):
            for instance, payload in raw.items():
                if not isinstance(payload, dict):
                    continue
                payload = {**payload, "__instance__": instance}
                merged.extend(self._per_instance.parse(payload, query))
        return self._dedupe_by_actor(merged)

    def _dedupe_by_actor(self, records: list[VideoRecord]) -> list[VideoRecord]:
        best: dict[str, VideoRecord] = {}
        for r in records:
            key = _actor_content_key(r)
            existing = best.get(key)
            if existing is None:
                best[key] = r
                continue
            existing_q = existing.quality_score or 0.0
            new_q = r.quality_score or 0.0
            if new_q > existing_q or (
                new_q == existing_q and (r.height or 0) > (existing.height or 0)
            ):
                best[key] = r
        return sorted(best.values(), key=lambda r: r.id)

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        if os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
            return []
        client = self.client()
        aggregated: list[VideoRecord] = []
        params = {
            "search": " ".join(query.terms),
            "count": str(min(query.max_results, 25)),
            "licenceOneOf[]": [str(i) for i in sorted(ALLOWED_LICENCE_IDS)],
        }
        for instance in self.instances:
            try:
                resp = client.get(f"{instance}/api/v1/search/videos", params=params)
                resp.raise_for_status()
                payload = resp.json()
                payload["__instance__"] = instance
            except (httpx.HTTPError, ValueError):
                continue
            aggregated.extend(self._per_instance.parse(payload, query))
        return self._dedupe_by_actor(aggregated)
