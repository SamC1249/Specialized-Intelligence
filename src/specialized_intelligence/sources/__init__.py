"""Source-discovery adapters.

Every source listed in `db_structured.md` section 1 has exactly one module
under this package. A source adapter knows how to:

* query the upstream API or federated index for candidate videos that match
  a topic (e.g. "cooking");
* return a uniform stream of `DiscoveredVideo` records;
* normalize the upstream license tag onto `LicenseNorm`.

Adapters never download bytes — that is the `acquire` stage's job.
"""
