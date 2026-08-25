"""PeerTube federation adapter — offline fixture over two instances."""

from __future__ import annotations

from specint.records import SourceQuery
from specint.sources.peertube_federation import PeerTubeFederationSource


def test_federation_dedupes_shared_video_across_two_instances(load_json):
    payload = {
        "https://framatube.org": load_json("peertube_federation/framatube_search.json"),
        "https://tilvids.com": load_json("peertube_federation/tilvids_search.json"),
    }
    records = PeerTubeFederationSource(instances=[]).parse(payload, SourceQuery(terms=["cooking"]))
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids))
    shared = [r for r in records if "shared-vid-1" in r.id]
    assert len(shared) == 1
    winner = shared[0]
    assert winner.height == 1080  # framatube copy should win on quality tiebreak


def test_federation_search_offline_returns_empty(monkeypatch):
    monkeypatch.delenv("SPECINT_RUN_INTEGRATION", raising=False)
    source = PeerTubeFederationSource(instances=["https://example.test"])
    assert list(source.search(SourceQuery(terms=["cooking"]))) == []


def test_federation_loads_seed_instance_list_by_default():
    source = PeerTubeFederationSource()
    assert source.instances, "seed instance list should be non-empty"
    assert all(url.startswith("https://") for url in source.instances)
