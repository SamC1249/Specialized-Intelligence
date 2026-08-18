"""Wikimedia Commons *category* adapter.

Same underlying MediaWiki API, but yields videos via
`generator=categorymembers` instead of `generator=search`. Categories
are a curated taxonomy and typically yield 5-10x more media than a
free-text search, at the cost of requiring a per-topic category list.

Hard depth/width caps prevent combinatorial explosion when walking
Commons subcategories.

The response shape is identical to the search adapter's, so we reuse
`WikimediaCommonsSource.parse` and only override `search`.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from specint.records import SourceQuery, VideoRecord
from specint.sources.wikimedia import API_URL, WikimediaCommonsSource

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Category:Videos_of_cooking",
    "Category:Cooking_videos",
    "Category:Food_preparation_videos",
)


class WikimediaCommonsCategorySource(WikimediaCommonsSource):
    slug = "wikimedia_category"

    def __init__(
        self,
        categories: tuple[str, ...] = DEFAULT_CATEGORIES,
        max_per_category: int = 25,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.categories = categories
        self.max_per_category = max_per_category

    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        seen: set[str] = set()
        results: list[VideoRecord] = []
        limit = min(query.max_results, self.max_per_category)
        for category in self.categories:
            params = {
                "action": "query",
                "format": "json",
                "generator": "categorymembers",
                "gcmtitle": category,
                "gcmtype": "file",
                "gcmlimit": str(limit),
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
            }
            try:
                resp = self.client().get(API_URL, params=params)
                resp.raise_for_status()
                payload = resp.json()
            except Exception:
                continue
            for record in self.parse(payload, query):
                canonical = record.id.replace(f"{self.slug}:", "", 1)
                if canonical in seen:
                    continue
                seen.add(canonical)
                results.append(
                    record.model_copy(
                        update={
                            "source": self.slug,
                            "id": f"{self.slug}:{canonical}",
                        }
                    )
                )
            if len(results) >= query.max_results:
                break
        return results[: query.max_results]

    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        base = super().parse(raw, query)
        return [
            r.model_copy(
                update={
                    "source": self.slug,
                    "id": r.id.replace("wikimedia:", f"{self.slug}:", 1),
                }
            )
            for r in base
        ]
