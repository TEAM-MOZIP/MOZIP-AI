# SERVER policy.domain.AgeGroup과 동일한 구간. (이름, 최소 나이, 최대 나이) — 경계값 포함.
AGE_GROUP_BANDS: list[tuple[str, int | None, int | None]] = [
    ("UNDER_19", None, 18),
    ("AGE_19_24", 19, 24),
    ("AGE_25_29", 25, 29),
    ("AGE_30_34", 30, 34),
    ("AGE_35_49", 35, 49),
    ("AGE_50_64", 50, 64),
    ("AGE_65_PLUS", 65, None),
]


def age_group_name(age: int) -> str:
    for name, band_min, band_max in AGE_GROUP_BANDS:
        if (band_min is None or age >= band_min) and (band_max is None or age <= band_max):
            return name
    raise AssertionError(f"AgeGroup 구간이 나이 {age}를 포함하지 않습니다.")  # pragma: no cover
