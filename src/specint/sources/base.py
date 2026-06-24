"""BaseSource ABC.

Every adapter is split into:
  - `parse(raw)`: pure, deterministic, fixture-testable.
  - `search(query)`: hits the network and yields records via `parse`.

This keeps unit tests offline and makes new adapters auditable in
isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

import httpx

from specint.records import SourceQuery, VideoRecord

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
USER_AGENT = "specint/0.1 (+https://github.com/SamC1249/Specialized-Intelligence)"


class BaseSource(ABC):
    """Abstract data source."""

    slug: str = ""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=DEFAULT_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    def search(self, query: SourceQuery) -> Iterable[VideoRecord]:
        """Yield VideoRecords for `query`. May do network I/O."""

    @abstractmethod
    def parse(self, raw: Any, query: SourceQuery) -> list[VideoRecord]:
        """Pure: turn a raw upstream payload into VideoRecords."""

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
