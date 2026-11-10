from hospital_analytics.dictionary import CODEBOOK, label


def test_every_interpretation_declares_source_and_status():
    for codes in CODEBOOK.values():
        assert codes.source and codes.description and codes.codes
        assert codes.status in {"secondary", "prior_knowledge"}  # nothing claims primary source


def test_ident_5_is_long_stay_not_continuation():
    assert label("IDENT", "5") == "Longa permanência"
    assert label("IDENT", "3") == "Continuação"
    assert label("IDENT", "9") is None
