import pyarrow as pa
import pytest

from evaluation.nemotron.sampling import (
    DistrictSampleShortageError,
    UnexpectedDistrictCountError,
    sample_seoul_personas,
)

_DISTRICT_COUNT = 25


def _build_seoul_like_table(
    rows_per_district: int, district_count: int = _DISTRICT_COUNT
) -> pa.Table:
    # 실제 서울 25개 구 이름 대신 합성 이름을 쓴다 — 이 테스트는 자치구별 표본
    # 추출 로직만 검증하면 되고 운영 ontology나 실제 dataset과 결합할 필요가 없다.
    sex_values, age_values, province_values, district_values = [], [], [], []
    for district_index in range(district_count):
        district = f"서울-TEST_DISTRICT_{district_index:02d}"
        for row_index in range(rows_per_district):
            sex_values.append("남자" if row_index % 2 == 0 else "여자")
            age_values.append(20 + row_index)
            province_values.append("서울")
            district_values.append(district)

    return pa.table(
        {
            "sex": sex_values,
            "age": age_values,
            "province": province_values,
            "district": district_values,
        }
    )


def test_sample_seoul_personas_returns_exact_quota_per_district():
    table = _build_seoul_like_table(rows_per_district=10)

    sampled = sample_seoul_personas(table, seed=1, samples_per_district=5)

    assert len(sampled) == _DISTRICT_COUNT * 5
    counts: dict[str, int] = {}
    for persona in sampled:
        counts[persona.district] = counts.get(persona.district, 0) + 1
    assert set(counts.values()) == {5}
    assert len(counts) == _DISTRICT_COUNT


def test_sample_seoul_personas_is_deterministic_for_same_seed():
    table = _build_seoul_like_table(rows_per_district=10)

    first = sample_seoul_personas(table, seed=7, samples_per_district=5)
    second = sample_seoul_personas(table, seed=7, samples_per_district=5)

    assert first == second


def test_sample_seoul_personas_no_replacement_within_district():
    # rows_per_district와 samples_per_district를 같게 두면, 중복 추출(=replacement)이
    # 있었을 경우에만 age 값에 중복이 생긴다(각 row가 서로 다른 age를 갖도록 구성했으므로).
    table = _build_seoul_like_table(rows_per_district=5)

    sampled = sample_seoul_personas(table, seed=3, samples_per_district=5)

    ages_by_district: dict[str, list[int]] = {}
    for persona in sampled:
        ages_by_district.setdefault(persona.district, []).append(persona.age)
    for ages in ages_by_district.values():
        assert len(ages) == len(set(ages))


def test_sample_seoul_personas_raises_when_district_short_of_quota():
    table = _build_seoul_like_table(rows_per_district=3)

    with pytest.raises(DistrictSampleShortageError):
        sample_seoul_personas(table, seed=1, samples_per_district=5)


def test_sample_seoul_personas_raises_when_district_count_is_not_25():
    table = _build_seoul_like_table(rows_per_district=10, district_count=3)

    with pytest.raises(UnexpectedDistrictCountError):
        sample_seoul_personas(table, seed=1, samples_per_district=5)
