from app.ontology.age_group import age_group_name


def test_age_group_name_returns_expected_band_for_representative_ages():
    assert age_group_name(10) == "UNDER_19"
    assert age_group_name(27) == "AGE_25_29"
    assert age_group_name(70) == "AGE_65_PLUS"


def test_age_group_name_boundary_values():
    assert age_group_name(18) == "UNDER_19"
    assert age_group_name(19) == "AGE_19_24"
    assert age_group_name(64) == "AGE_50_64"
    assert age_group_name(65) == "AGE_65_PLUS"


def test_age_group_name_is_deterministic():
    assert age_group_name(30) == age_group_name(30)
