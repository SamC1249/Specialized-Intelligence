from specint.quality import SEED_TERMS, SUPPORTED_LANGS, all_seed_terms, seed_terms_for


def test_supported_langs_covers_core_families():
    assert {"en", "es", "fr", "ja", "zh", "hi", "ar"}.issubset(set(SUPPORTED_LANGS))


def test_seed_terms_for_is_case_insensitive():
    assert seed_terms_for("en") == seed_terms_for("EN")
    assert seed_terms_for("zz") == []


def test_all_seed_terms_deduplicates_and_preserves_order():
    only_en = all_seed_terms(["en"])
    assert only_en == SEED_TERMS["en"]

    both = all_seed_terms(["en", "en", "es"])
    assert both[: len(only_en)] == only_en
    assert "cocina" in both
    assert len(both) == len(set(both))


def test_all_seed_terms_defaults_to_full_union():
    full = all_seed_terms(None)
    # Every language must contribute at least one seed term.
    for lang, terms in SEED_TERMS.items():
        assert any(t in full for t in terms), lang
