from specint.records import License, SourceQuery
from specint.sources.archive_org import ArchiveOrgSource


def test_archive_org_parse_classifies_license_and_duration(load_json):
    raw = load_json("archive_org/search_cooking.json")
    src = ArchiveOrgSource()
    records = src.parse(raw, SourceQuery(terms=["cooking"], max_results=10))
    assert len(records) == 3
    by_id = {r.source_native_id: r for r in records}

    pd = by_id["PrelingerCookingShow1952"]
    assert pd.license is License.PUBLIC_DOMAIN
    assert pd.duration_s == 18 * 60 + 42
    assert pd.media_url is not None
    assert "cooking" in pd.keywords

    cc_by = by_id["ChefDemo2018"]
    assert cc_by.license is License.CC_BY
    assert cc_by.duration_s == 4 * 60 + 30
    assert cc_by.media_url is not None

    nc = by_id["RestrictedRecipe"]
    assert nc.license is License.RESTRICTED
    assert nc.media_url is None
