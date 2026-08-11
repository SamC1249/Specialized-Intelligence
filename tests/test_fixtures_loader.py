from pathlib import Path

from specint.compare import load_fixture_by_source
from specint.records import SourceQuery


def test_load_fixture_by_source_reads_all_sources(fixtures_dir: Path):
    q = SourceQuery(terms=["cooking", "recipe"], max_results=10)
    by_source = load_fixture_by_source(fixtures_dir, q)
    assert set(by_source) >= {"wikimedia", "archive_org", "peertube", "common_crawl"}
    for slug in ("wikimedia", "archive_org", "peertube", "common_crawl"):
        assert isinstance(by_source[slug], list)
    assert len(by_source["wikimedia"]) >= 1
