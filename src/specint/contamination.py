"""Eval-set contamination guard.

Standard video eval sets (YouCook2, EPIC-KITCHENS-100, HD-EPIC, …) are
public; if a candidate training record overlaps with an eval clip — same
URL, same upstream id, or a near-identical title — we silently leak
training signal into evaluation. This module gives the pipeline a
*blocklist* primitive so the leakage is caught at curation time.

The blocklist is a JSONL file. One blocklist entry per line, each of the
form::

    {"kind": "title_norm",  "value": "knife skills"}
    {"kind": "url",         "value": "https://example.test/clip-1234"}
    {"kind": "native_id",   "value": "<source-native-id>"}
    {"kind": "phash16",     "value": "abc123..."}   # reserved for v1

For v0 we implement ``title_norm``, ``url`` and ``native_id``.
``phash16`` (16-byte DCT pHash hex string) is a *schema reservation*
for the byte-level dedup module that lands once frame extraction is
online; today the loader accepts it but the matcher is intentionally a
no-op so blocklists are forward-compatible.

The matcher is **conservative**: false negatives are bad (leakage); the
real cost of a false positive is only a slightly smaller training
corpus, which we accept. Title normalisation strips diacritics and
stop-words so "How to chop an onion" matches "How to chop an onion!"
matches "how to chop onion" — without becoming so permissive that it
matches every cooking video.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from specint.records import VideoRecord

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")
STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "without",
    }
)

VALID_KINDS: frozenset[str] = frozenset({"title_norm", "url", "native_id", "phash16"})


def normalize_title(title: str) -> str:
    """Lowercase + strip diacritics + drop punctuation + drop stop-words.

    Deterministic: identical inputs → identical outputs. Empty/None
    inputs become the empty string so they never match.
    """
    if not title:
        return ""
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    lowered = ascii_only.lower()
    no_punct = _PUNCT_RE.sub(" ", lowered)
    tokens = [t for t in _WS_RE.split(no_punct) if t and t not in STOP_WORDS]
    return " ".join(tokens)


@dataclass(frozen=True)
class BlocklistEntry:
    kind: str
    value: str

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(
                f"unsupported blocklist kind {self.kind!r} (valid: {sorted(VALID_KINDS)})"
            )


@dataclass(frozen=True)
class Blocklist:
    """In-memory representation of a contamination blocklist."""

    titles: frozenset[str] = field(default_factory=frozenset)
    urls: frozenset[str] = field(default_factory=frozenset)
    native_ids: frozenset[str] = field(default_factory=frozenset)
    phash16: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_entries(cls, entries: Iterable[BlocklistEntry]) -> Blocklist:
        titles: set[str] = set()
        urls: set[str] = set()
        native_ids: set[str] = set()
        phash16: set[str] = set()
        for entry in entries:
            if entry.kind == "title_norm":
                titles.add(normalize_title(entry.value))
            elif entry.kind == "url":
                urls.add(entry.value.strip().rstrip("/"))
            elif entry.kind == "native_id":
                native_ids.add(entry.value.strip())
            elif entry.kind == "phash16":
                phash16.add(entry.value.strip().lower())
        return cls(
            titles=frozenset(titles - {""}),
            urls=frozenset(urls - {""}),
            native_ids=frozenset(native_ids - {""}),
            phash16=frozenset(phash16 - {""}),
        )

    @classmethod
    def load(cls, path: str | Path) -> Blocklist:
        p = Path(path)
        entries: list[BlocklistEntry] = []
        for raw in p.read_text().splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            payload = json.loads(raw)
            entries.append(BlocklistEntry(kind=payload["kind"], value=str(payload["value"])))
        return cls.from_entries(entries)

    def contains(self, record: VideoRecord) -> bool:
        """Return True if any matcher trips on ``record``.

        ``phash16`` is reserved for the byte-level dedup module and is a
        no-op until a record carries a ``phash16`` annotation — see the
        module docstring.
        """
        if self.urls and str(record.url).strip().rstrip("/") in self.urls:
            return True
        if self.native_ids and record.source_native_id in self.native_ids:
            return True
        return bool(self.titles and normalize_title(record.title) in self.titles)

    def is_empty(self) -> bool:
        return not (self.titles or self.urls or self.native_ids or self.phash16)


def filter_contaminated(
    records: Iterable[VideoRecord],
    blocklist: Blocklist,
) -> tuple[list[VideoRecord], list[VideoRecord]]:
    """Split ``records`` into ``(kept, dropped)``.

    Returning both halves makes the audit trail explicit — the pipeline
    should write the dropped list to a `contaminated.jsonl` manifest so
    the contamination ledger is reviewable.
    """
    kept: list[VideoRecord] = []
    dropped: list[VideoRecord] = []
    for record in records:
        (dropped if blocklist.contains(record) else kept).append(record)
    return kept, dropped


def iter_contaminated(
    records: Iterable[VideoRecord],
    blocklist: Blocklist,
) -> Iterator[VideoRecord]:
    for record in records:
        if blocklist.contains(record):
            yield record
