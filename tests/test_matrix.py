from __future__ import annotations

from specint.compare import load_suite, run_matrix
from specint.records import SourceQuery, SourceQuerySuite


def test_run_matrix_across_query_suite():
    by_query_source = load_suite()
    queries = []
    for key in by_query_source:
        terms_part = key.split(";", 1)[0]
        terms = [t for t in terms_part.removeprefix("terms=").split("|") if t]
        queries.append(SourceQuery(terms=terms, max_results=25))
    suite = SourceQuerySuite(name="cooking-suite-test", queries=queries)
    rows = run_matrix(suite, by_query_source, notes="unit-test")

    # Per-query rows + per-source aggregate + grand total
    per_query = [r for r in rows if "__suite_aggregate__" not in r.notes]
    aggregates = [r for r in rows if "__suite_aggregate__" in r.notes]
    assert per_query, "matrix must emit per-(query, source) rows"
    assert aggregates, "matrix must emit per-source suite aggregates"
    total = next(r for r in rows if r.source == "__total__")
    assert total.n_records >= 1
    assert total.scorer == "v1"
    assert total.notes.endswith("__suite_aggregate__")


def test_run_matrix_v2_populates_scorer_field():
    by_query_source = load_suite()
    queries = []
    for key in by_query_source:
        terms_part = key.split(";", 1)[0]
        terms = [t for t in terms_part.removeprefix("terms=").split("|") if t]
        queries.append(SourceQuery(terms=terms, max_results=25))
    suite = SourceQuerySuite(name="cooking-suite-test", queries=queries)
    rows = run_matrix(suite, by_query_source, notes="unit-test", scorer="v2")
    assert all(r.scorer == "v2" for r in rows)
