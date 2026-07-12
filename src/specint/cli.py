"""`python -m specint` CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from specint.compare import run_ablation, run_comparison
from specint.compare.harness import aggregate
from specint.domains import DEFAULT_DOMAIN, get_domain, list_domains
from specint.pipeline import dedup_records
from specint.records import SourceQuery
from specint.sources import REGISTRY


def _cmd_sources(_: argparse.Namespace) -> int:
    for slug, cls in sorted(REGISTRY.items()):
        print(f"{slug}\t{cls.__module__}.{cls.__name__}")
    return 0


def _cmd_domains(_: argparse.Namespace) -> int:
    for d in list_domains():
        terms = ",".join(d.seed_terms[:3]) + ("..." if len(d.seed_terms) > 3 else "")
        print(f"{d.slug}\t{d.display_name}\tseed_terms={terms}")
    return 0


def _resolve_domain(slug: str | None) -> object:
    if not slug:
        return DEFAULT_DOMAIN
    return get_domain(slug)


def _cmd_compare(args: argparse.Namespace) -> int:
    domain = _resolve_domain(args.domain)
    terms = args.terms or list(domain.seed_terms[:2])
    query = SourceQuery(terms=terms, max_results=args.max_results)
    only = set(args.only) if args.only else None

    by_source: dict[str, list] = {}
    if args.fixtures:
        for slug in REGISTRY:
            if only and slug not in only:
                continue
            by_source[slug] = []
    elif os.environ.get("SPECINT_RUN_INTEGRATION") != "1":
        print(
            "refusing to hit live network without SPECINT_RUN_INTEGRATION=1; "
            "pass --fixtures for an offline dry run.",
            file=sys.stderr,
        )
        return 2
    else:
        for slug, cls in REGISTRY.items():
            if only and slug not in only:
                continue
            try:
                records = list(cls().search(query))
            except Exception as exc:  # pragma: no cover - integration only
                print(f"[warn] {slug} failed: {exc}", file=sys.stderr)
                records = []
            by_source[slug] = records

    rows = run_comparison(
        query,
        by_source,
        notes=args.notes or "",
        domain=domain,
        with_dedup=not args.no_dedup,
    )
    payload = {
        "domain": domain.slug,
        "query": query.model_dump(mode="json"),
        "rows": [r.model_dump(mode="json") for r in rows],
    }

    out_path = (
        Path(args.output)
        if args.output
        else Path("reports") / f"compare-{date.today().isoformat()}-{domain.slug}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_ablate(args: argparse.Namespace) -> int:
    domain = _resolve_domain(args.domain)
    fixtures_dir = Path(args.fixtures_dir)
    from specint.sources.archive_org import ArchiveOrgSource
    from specint.sources.common_crawl import CommonCrawlRecipeSource
    from specint.sources.peertube import PeerTubeSource
    from specint.sources.wikimedia import WikimediaCommonsSource

    query = SourceQuery(terms=list(domain.seed_terms[:2]), max_results=25)
    records = []
    records.extend(
        WikimediaCommonsSource().parse(
            json.loads((fixtures_dir / "wikimedia/search_pasta.json").read_text()), query
        )
    )
    records.extend(
        ArchiveOrgSource().parse(
            json.loads((fixtures_dir / "archive_org/search_cooking.json").read_text()), query
        )
    )
    records.extend(
        PeerTubeSource().parse(
            json.loads((fixtures_dir / "peertube/search_cooking.json").read_text()), query
        )
    )
    for html_name in sorted((fixtures_dir / "common_crawl").glob("*.html")):
        records.extend(
            CommonCrawlRecipeSource().parse(
                {"html": html_name.read_text(), "url": f"https://example.test/{html_name.stem}"},
                query,
            )
        )

    result = run_ablation(records, domain=domain)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload)
    print(payload)
    return 0


def _cmd_dedup(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.input).read_text())
    raws = data["records"] if isinstance(data, dict) and "records" in data else data
    from specint.records import VideoRecord

    records = [VideoRecord.model_validate(r) for r in raws]
    result = dedup_records(records)
    before = aggregate("__before__", query_terms=[], records=records)
    after = aggregate("__after__", query_terms=[], records=result.records)
    payload = {
        "counters": result.counters,
        "before": before.model_dump(mode="json"),
        "after": after.model_dump(mode="json"),
        "duplicates": result.duplicates,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="specint")
    sub = p.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="list registered sources")
    p_sources.set_defaults(func=_cmd_sources)

    p_domains = sub.add_parser("domains", help="list registered domains")
    p_domains.set_defaults(func=_cmd_domains)

    p_cmp = sub.add_parser("compare", help="run the comparison harness")
    p_cmp.add_argument("--terms", nargs="*", help="search terms (default: domain seed terms)")
    p_cmp.add_argument("--only", nargs="*", help="restrict to these source slugs")
    p_cmp.add_argument("--max-results", type=int, default=25)
    p_cmp.add_argument("--fixtures", action="store_true", help="offline mode (no network)")
    p_cmp.add_argument("--output", help="output JSON path")
    p_cmp.add_argument("--notes", help="free-form note attached to every row")
    p_cmp.add_argument("--domain", help="domain slug (default: cooking)")
    p_cmp.add_argument("--no-dedup", action="store_true", help="skip __total_deduped__ row")
    p_cmp.set_defaults(func=_cmd_compare)

    p_abl = sub.add_parser("ablate", help="run scorer ablation on the fixture corpus")
    p_abl.add_argument("--domain", help="domain slug (default: cooking)")
    p_abl.add_argument(
        "--fixtures-dir",
        default=str(Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"),
        help="path to tests/fixtures",
    )
    p_abl.add_argument("--output", help="output JSON path")
    p_abl.set_defaults(func=_cmd_ablate)

    p_dedup = sub.add_parser("dedup", help="dedup a JSON list of VideoRecord dicts")
    p_dedup.add_argument("input", help="JSON file: list of records or {records: [...]}")
    p_dedup.set_defaults(func=_cmd_dedup)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
